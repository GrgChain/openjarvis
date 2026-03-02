"""HTTP API channel — synchronous POST /chat request/response."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from aiohttp import web
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import HttpApiConfig


class HttpApiChannel(BaseChannel):
    """HTTP API channel that exposes POST /chat for synchronous agent interaction."""

    name = "http_api"

    def __init__(self, config: HttpApiConfig, bus: MessageBus, workspace: Path | None = None,
                 cron_store_path: Path | None = None):
        super().__init__(config, bus)
        # Map chat_id → queue waiting for the final agent response
        self._pending: dict[str, asyncio.Queue[str]] = {}
        self._runner: web.AppRunner | None = None
        self._workspace = workspace
        self._cron_store_path = cron_store_path

    # ------------------------------------------------------------------
    # BaseChannel interface
    # ------------------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        app = web.Application()
        app.router.add_post("/chat", self._handle_chat)
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/sessions", self._handle_sessions_list)
        app.router.add_get("/sessions/{key}", self._handle_session_detail)
        app.router.add_get("/workspace/tree", self._handle_workspace_tree)
        app.router.add_get("/skills", self._handle_skills_list)
        app.router.add_get("/crons", self._handle_crons_list)

        # Serve frontend website if available
        # Find website/dist path relative to the nanobot deployment
        # In docker this will be /app/website/dist
        current_dir = Path(__file__).parent
        # Try to find the openjarvis root
        root_dir = current_dir.parent.parent.parent
        web_dist = root_dir / "website" / "dist"
        
        # Or check if we are already in /app (docker)
        if not web_dist.exists() and Path("/app/website/dist").exists():
            web_dist = Path("/app/website/dist")
            
        if web_dist.exists() and web_dist.is_dir():
            logger.info("Website UI found at {}, serving on /", web_dist)
            app.router.add_static("/assets", str(web_dist / "assets"), name="assets")
            # For Vite we also might have other static files in public
            
            # Catch-all for SPA routing (returns index.html)
            async def index_handler(request: web.Request) -> web.Response:
                # If requesting a specific file that might exist but isn't in /assets (e.g. favicon.ico)
                file_path = web_dist / request.path.lstrip("/")
                if request.path != "/" and file_path.exists() and file_path.is_file():
                    return web.FileResponse(file_path)
                return web.FileResponse(web_dist / "index.html")

            # Route for exactly "/"
            app.router.add_get("/", index_handler)
            # Route for all other paths (the regex /{path:.*} catches them)
            app.router.add_get("/{path:.*}", index_handler)
        else:
            logger.debug("Website UI not found at {}, UI will not be served", web_dist)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.config.host, self.config.port)
        await site.start()
        logger.info("HTTP API channel listening on {}:{}", self.config.host, self.config.port)

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def send(self, msg: OutboundMessage) -> None:
        """Deliver final agent response to the waiting HTTP request."""
        if msg.metadata.get("_progress"):
            # Skip streaming progress / tool-hint messages
            return
        queue = self._pending.get(msg.chat_id)
        if queue is not None:
            await queue.put(msg.content)

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _handle_chat(self, request: web.Request) -> web.Response:
        try:
            body: dict[str, Any] = await request.json()
        except Exception:
            return web.json_response({"error": "invalid JSON"}, status=400)

        sender_id = body.get("sender_id", "")
        chat_id = body.get("chat_id", "")
        content = body.get("content", "")

        if not sender_id or not chat_id or not content:
            return web.json_response({"error": "missing fields"}, status=400)

        if not self.is_allowed(sender_id):
            logger.warning("HTTP API access denied for sender_id={}", sender_id)
            return web.json_response({"error": "access denied"}, status=403)

        # Register a response queue before publishing so we don't miss the reply
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._pending[chat_id] = queue

        try:
            await self._handle_message(sender_id=sender_id, chat_id=chat_id, content=content)

            try:
                reply = await asyncio.wait_for(queue.get(), timeout=self.config.timeout_s)
            except asyncio.TimeoutError:
                return web.json_response({"error": "request timed out"}, status=408)

            return web.json_response({"content": reply, "chat_id": chat_id})
        finally:
            self._pending.pop(chat_id, None)

    async def _handle_sessions_list(self, request: web.Request) -> web.Response:
        """GET /sessions — list all sessions with metadata and message count."""
        if self._workspace is None:
            return web.json_response({"error": "session storage not configured"}, status=503)

        from nanobot.session.manager import SessionManager

        sm = SessionManager(self._workspace)
        items = sm.list_sessions()

        sessions = []
        for item in items:
            key = item.get("key", "")
            # Load message count without caching
            session = sm._load(key)
            sessions.append({
                "key": key,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "message_count": len(session.messages) if session else 0,
            })

        return web.json_response({"sessions": sessions})

    async def _handle_session_detail(self, request: web.Request) -> web.Response:
        """GET /sessions/{key} — return conversation messages for a session."""
        if self._workspace is None:
            return web.json_response({"error": "session storage not configured"}, status=503)

        key = request.match_info["key"]  # aiohttp URL-decodes automatically

        from nanobot.session.manager import SessionManager

        sm = SessionManager(self._workspace)
        session = sm._load(key)
        if session is None:
            return web.json_response({"error": "session not found"}, status=404)

        messages = []
        for m in session.messages:
            role = m.get("role")
            if role == "user":
                messages.append({
                    "role": "user",
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp"),
                })
            elif role == "assistant":
                entry: dict = {
                    "role": "assistant",
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp"),
                }
                tool_calls = m.get("tool_calls")
                if tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name"),
                            "arguments": tc.get("function", {}).get("arguments"),
                        }
                        for tc in tool_calls
                    ]
                messages.append(entry)
            elif role == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id"),
                    "name": m.get("name"),
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp"),
                })

        return web.json_response({
            "key": key,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": len(session.messages),
            "messages": messages,
        })

    async def _handle_workspace_tree(self, request: web.Request) -> web.Response:
        """GET /workspace/tree?depth=N — return workspace directory tree."""
        if self._workspace is None:
            return web.json_response({"error": "workspace not configured"}, status=503)

        if not self._workspace.exists():
            return web.json_response({"error": "workspace not found"}, status=404)

        try:
            raw_depth = request.rel_url.query.get("depth")
            max_depth = min(int(raw_depth), 10) if raw_depth is not None else 10
        except ValueError:
            return web.json_response({"error": "depth must be an integer"}, status=400)

        tree = self._build_tree(self._workspace, self._workspace, depth=0, max_depth=max_depth)
        return web.json_response(tree)

    async def _handle_skills_list(self, request: web.Request) -> web.Response:
        """GET /skills — list all available skills with metadata."""
        if self._workspace is None:
            return web.json_response({"error": "workspace not configured"}, status=503)

        from nanobot.agent.skills import SkillsLoader

        loader = SkillsLoader(self._workspace)
        all_skills = loader.list_skills(filter_unavailable=False)

        skills = []
        for s in all_skills:
            meta = loader.get_skill_metadata(s["name"]) or {}
            nanobot_meta = loader._get_skill_meta(s["name"])
            available = loader._check_requirements(nanobot_meta)
            skills.append({
                "name": s["name"],
                "description": meta.get("description", s["name"]),
                "emoji": nanobot_meta.get("emoji", ""),
                "source": s["source"],
                "available": available,
                "always": bool(nanobot_meta.get("always") or meta.get("always")),
            })

        return web.json_response({"skills": skills})

    async def _handle_crons_list(self, request: web.Request) -> web.Response:
        """GET /crons — list all cron jobs (enabled and disabled)."""
        if self._cron_store_path is None:
            return web.json_response({"error": "cron store not configured"}, status=503)

        from nanobot.cron.service import CronService

        svc = CronService(self._cron_store_path)
        jobs = svc.list_jobs(include_disabled=True)

        return web.json_response({
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "enabled": j.enabled,
                    "delete_after_run": j.delete_after_run,
                    "schedule": {
                        "kind": j.schedule.kind,
                        "at_ms": j.schedule.at_ms,
                        "every_ms": j.schedule.every_ms,
                        "expr": j.schedule.expr,
                        "tz": j.schedule.tz,
                    },
                    "payload": {
                        "kind": j.payload.kind,
                        "message": j.payload.message,
                        "deliver": j.payload.deliver,
                        "channel": j.payload.channel,
                        "to": j.payload.to,
                    },
                    "state": {
                        "next_run_at_ms": j.state.next_run_at_ms,
                        "last_run_at_ms": j.state.last_run_at_ms,
                        "last_status": j.state.last_status,
                        "last_error": j.state.last_error,
                    },
                    "created_at_ms": j.created_at_ms,
                    "updated_at_ms": j.updated_at_ms,
                }
                for j in jobs
            ]
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_tree(
        self, root: Path, path: Path, *, depth: int, max_depth: int
    ) -> dict[str, Any]:
        """Recursively build a JSON-serialisable tree node for *path*."""
        stat = path.stat()
        rel = path.relative_to(root)
        node: dict[str, Any] = {
            "name": path.name,
            "path": str(rel) if rel != Path(".") else "",
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size if path.is_file() else None,
            "modified": stat.st_mtime,
        }

        if path.is_dir() and depth < max_depth:
            children = []
            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except PermissionError:
                entries = []
            for entry in entries:
                children.append(
                    self._build_tree(root, entry, depth=depth + 1, max_depth=max_depth)
                )
            node["children"] = children

        return node
