"""WebSocket /ws/chat endpoint."""

from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.channels.base import BaseChannel

router = APIRouter()

# Uploaded files live here — same path as routes/files.py
_UPLOADS_DIR = Path.home() / ".nanobot" / "uploads"

# Match markdown image links pointing to /api/files/...
_IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(/api/files/([^)]+\.(?:png|jpe?g|gif|webp|bmp))\)", re.IGNORECASE)


def _extract_media_paths(content: str) -> list[str]:
    """Extract local file paths for images referenced as ![...](/api/files/xxx)."""
    paths: list[str] = []
    for m in _IMAGE_MD_RE.finditer(content):
        filename = m.group(1)
        fp = _UPLOADS_DIR / filename
        if fp.is_file():
            paths.append(str(fp))
    return paths


class WebChannel(BaseChannel):
    """
    A nanobot Channel implementation for the Web interface.
    
    Instead of patching tools, this channel integrates with the standard
    message bus. It allows multiple WebSocket connections (for the same user)
    to receive the same messages (fan-out).
    """
    name = "web"
    display_name = "Web"

    def __init__(self, config: Any, bus: Any):
        super().__init__(config, bus)
        # chat_id (user_id) -> list[asyncio.Queue[dict]]
        self.queues: dict[str, list[asyncio.Queue]] = {}
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        """Receive an OutboundMessage from the bus and route to WebSockets."""
        queues = self.queues.get(str(msg.chat_id), [])
        if not queues:
            return

        # Prepare the payload once
        content = msg.content or ""
        # Append media as markdown images so the web UI can render them
        if msg.media:
            for m_path in msg.media:
                fname = Path(m_path).name
                if f"/api/files/{fname}" not in content:
                    # Avoid duplication if already in content
                    content += f"\n\n![image](/api/files/{fname})"

        payload = {
            "type": "progress" if msg.metadata.get("_progress") else "done",
            "content": content,
        }
        if msg.metadata.get("_tool_hint"):
            payload["tool_hint"] = True

        # Fan-out to all active queues for this chat_id
        for q in queues:
            try:
                await q.put(payload)
            except Exception:
                pass

    def register_queue(self, chat_id: str, q: asyncio.Queue) -> None:
        self.queues.setdefault(str(chat_id), []).append(q)

    def unregister_queue(self, chat_id: str, q: asyncio.Queue) -> None:
        cid = str(chat_id)
        if cid in self.queues:
            if q in self.queues[cid]:
                self.queues[cid].remove(q)
            if not self.queues[cid]:
                self.queues.pop(cid)


def _ensure_web_channel(container: Any) -> WebChannel:
    """Ensure the 'web' channel is registered in the ChannelManager."""
    if "web" not in container.channels.channels:
        # Pass a minimal config object
        from dataclasses import dataclass
        @dataclass
        class SimpleConfig:
            enabled: bool = True
            allow_from: list[str] = None
        
        cfg = SimpleConfig(allow_from=["*"])
        channel = WebChannel(cfg, container.bus)
        container.channels.channels["web"] = channel
        logger.info("WebChannel registered dynamically")
    return container.channels.channels["web"]


async def _auth_websocket(websocket: WebSocket) -> dict | None:
    """Validate the JWT token sent as query param ``token=...``."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None

    from server.api.auth import decode_access_token
    import jwt

    user_store = websocket.app.state.user_store
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return None

    user = user_store.get_by_id(payload["sub"])
    if not user:
        await websocket.close(code=4001, reason="User not found")
        return None

    return user


async def _archive_session(container: Any, session_key: str) -> bool:
    """Archive unconsolidated messages of a session (like CLI /new command)."""
    session = container.session_manager.get_or_create(session_key)
    if not session.messages:
        return True
    try:
        ok = await container.agent.memory_consolidator.archive_unconsolidated(session)
        if ok:
            session.clear()
            container.session_manager.save(session)
            container.session_manager.invalidate(session_key)
        return ok
    except Exception:
        logger.exception("Memory archival failed for {}", session_key)
        return False


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """
    WebSocket chat endpoint.
    """
    user = await _auth_websocket(websocket)
    if user is None:
        return

    await websocket.accept()
    container = websocket.app.state.services
    if container is None:
        await websocket.close()
        return

    # Initialize dynamic WebChannel if needed
    web_channel = _ensure_web_channel(container)
    
    # Per-connection queue for receiving OutboundMessages from the WebChannel
    conn_q: asyncio.Queue[dict] = asyncio.Queue()
    uid = str(user["id"])
    web_channel.register_queue(uid, conn_q)

    # Determine session key
    requested_key: str | None = websocket.query_params.get("session")
    session_key = (
        requested_key
        if requested_key and requested_key.startswith(f"web:{user['id']}")
        else f"web:{user['id']}:{uuid.uuid4().hex[:8]}"
    )
    await websocket.send_json({"type": "session_info", "session_key": session_key})

    # Background task: forward messages from conn_q to the WebSocket
    async def _send_loop():
        try:
            while True:
                payload = await conn_q.get()
                await websocket.send_json(payload)
        except Exception:
            pass

    send_task = asyncio.create_task(_send_loop())

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type")

            if msg_type == "cancel":
                # Use standard agent capability to stop tasks for this session
                stop_msg = InboundMessage(
                    channel="web",
                    sender_id=str(user["id"]),
                    chat_id=str(user["id"]),
                    content="/stop",
                    session_key_override=session_key
                )
                await container.bus.publish_inbound(stop_msg)

            elif msg_type == "new_session":
                old_key = session_key
                session_key = f"web:{user['id']}:{uuid.uuid4().hex[:8]}"
                await websocket.send_json({"type": "session_info", "session_key": session_key})
                asyncio.create_task(_archive_session(container, old_key))

            elif msg_type == "message":
                content = raw.get("content", "").strip()
                msg_session_key = raw.get("session_key")
                if msg_session_key and msg_session_key.startswith(f"web:{user['id']}"):
                    if msg_session_key != session_key:
                        session_key = msg_session_key
                        await websocket.send_json({"type": "session_info", "session_key": session_key})
                
                if not content:
                    continue

                # Prepare the InboundMessage
                media_paths = _extract_media_paths(content)
                inbound = InboundMessage(
                    channel="web",
                    sender_id=str(user["id"]),
                    chat_id=str(user["id"]),
                    content=content,
                    media=media_paths,
                    session_key_override=session_key,
                )
                # Publish to the bus — standard AgentLoop.run() will pick it up
                await container.bus.publish_inbound(inbound)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("ws_chat error: {}", exc)
    finally:
        send_task.cancel()
        web_channel.unregister_queue(uid, conn_q)
