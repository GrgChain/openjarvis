"""Config routes: agent settings and gateway config."""

from __future__ import annotations

import datetime
import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from server.api.deps import get_services, require_admin
from server.api.gateway import ServiceContainer
from server.api.models import (
    AgentSettingsRequest,
    AgentSettingsResponse,
    GatewayConfigRequest,
    GatewayConfigResponse,
    HeartbeatConfigModel,
)
from nanobot.config.schema import Config

router = APIRouter()

# Workspace markdown files that are allowed to be read/written via the API
_WORKSPACE_FILES = {"AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "HEARTBEAT.md"}


def _mask(value: str) -> str:
    """Mask an API key, showing only the last 4 characters."""
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"


@router.get("/agent", response_model=AgentSettingsResponse)
async def get_agent_settings(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> AgentSettingsResponse:
    d = svc.config.agents.defaults
    t = svc.config.tools
    ch = svc.config.channels
    return AgentSettingsResponse(
        model=d.model,
        provider=d.provider,
        max_tokens=d.max_tokens,
        temperature=d.temperature,
        max_iterations=d.max_tool_iterations,
        context_window_tokens=d.context_window_tokens,
        reasoning_effort=d.reasoning_effort,
        workspace=d.workspace,
        restrict_to_workspace=t.restrict_to_workspace,
        exec_timeout=t.exec.timeout,
        path_append=t.exec.path_append,
        web_search_api_key=_mask(t.web.search.api_key),
        web_proxy=t.web.proxy,
        send_progress=ch.send_progress,
        send_tool_hints=ch.send_tool_hints,
    )


@router.patch("/agent", response_model=AgentSettingsResponse)
async def update_agent_settings(
    body: AgentSettingsRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> AgentSettingsResponse:
    from nanobot.config.loader import save_config

    d = svc.config.agents.defaults
    t = svc.config.tools
    ch = svc.config.channels

    if body.model is not None:
        d.model = body.model
    if body.provider is not None:
        d.provider = body.provider
    if body.max_tokens is not None:
        d.max_tokens = body.max_tokens
    if body.temperature is not None:
        d.temperature = body.temperature
    if body.max_iterations is not None:
        d.max_tool_iterations = body.max_iterations
    if body.context_window_tokens is not None:
        d.context_window_tokens = body.context_window_tokens
    if body.reasoning_effort is not None:
        d.reasoning_effort = body.reasoning_effort
    if body.workspace is not None:
        d.workspace = body.workspace
    if body.restrict_to_workspace is not None:
        t.restrict_to_workspace = body.restrict_to_workspace
    if body.exec_timeout is not None:
        t.exec.timeout = body.exec_timeout
    if body.path_append is not None:
        t.exec.path_append = body.path_append
    if body.web_search_api_key is not None:
        t.web.search.api_key = body.web_search_api_key
    if body.web_proxy is not None:
        t.web.proxy = body.web_proxy or None
    if body.send_progress is not None:
        ch.send_progress = body.send_progress
    if body.send_tool_hints is not None:
        ch.send_tool_hints = body.send_tool_hints

    save_config(svc.config)
    svc.reload_provider()
    return await get_agent_settings(_admin, svc)


@router.get("/gateway", response_model=GatewayConfigResponse)
async def get_gateway_config(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> GatewayConfigResponse:
    g = svc.config.gateway
    return GatewayConfigResponse(
        host=g.host,
        port=g.port,
        heartbeat=HeartbeatConfigModel(
            enabled=g.heartbeat.enabled,
            interval_s=g.heartbeat.interval_s,
        ),
    )


@router.patch("/gateway", response_model=GatewayConfigResponse)
async def update_gateway_config(
    body: GatewayConfigRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> GatewayConfigResponse:
    from nanobot.config.loader import save_config

    g = svc.config.gateway
    if body.host is not None:
        g.host = body.host
    if body.port is not None:
        g.port = body.port
    if body.heartbeat_enabled is not None:
        g.heartbeat.enabled = body.heartbeat_enabled
    if body.heartbeat_interval_s is not None:
        g.heartbeat.interval_s = body.heartbeat_interval_s

    save_config(svc.config)
    return await get_gateway_config(_admin, svc)


@router.get("/workspace-file/{name}")
async def get_workspace_file(
    name: str,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    if name not in _WORKSPACE_FILES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"File '{name}' not allowed")
    workspace = Path(svc.config.agents.defaults.workspace).expanduser()
    path = workspace / name
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return {"name": name, "content": content}


@router.put("/workspace-file/{name}")
async def put_workspace_file(
    name: str,
    body: dict,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    if name not in _WORKSPACE_FILES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"File '{name}' not allowed")
    content: str = body.get("content", "")
    workspace = Path(svc.config.agents.defaults.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / name).write_text(content, encoding="utf-8")
    return {"name": name, "content": content}


@router.get("/workspace/tree")
async def get_workspace_tree(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Return a recursive tree of the workspace directory."""
    workspace = Path(svc.config.agents.defaults.workspace).expanduser().resolve()

    # Directories to exclude (too large or not useful)
    _EXCLUDED_DIRS = {"sessions", "__pycache__", "skills"}

    def _build_tree(root: Path) -> list[dict]:
        nodes: list[dict] = []
        if not root.is_dir():
            return nodes
        try:
            entries = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return nodes
        for entry in entries:
            # Skip hidden files/dirs
            if entry.name.startswith("."):
                continue
            rel = str(entry.relative_to(workspace))
            if entry.is_dir():
                if entry.name in _EXCLUDED_DIRS:
                    continue
                nodes.append({
                    "name": entry.name,
                    "path": rel,
                    "type": "dir",
                    "children": _build_tree(entry),
                })
            else:
                nodes.append({
                    "name": entry.name,
                    "path": rel,
                    "type": "file",
                })
        return nodes

    return {"tree": _build_tree(workspace)}


@router.get("/workspace/file")
async def get_workspace_file_by_path(
    path: str,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Read any text file within the workspace directory by relative path."""
    workspace = Path(svc.config.agents.defaults.workspace).expanduser().resolve()
    target = (workspace / path).resolve()
    # Prevent path traversal
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Path outside workspace")
    if not target.exists() or not target.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"File not found: {path}")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a text file")
    return {"name": target.name, "path": path, "content": content}


@router.put("/workspace/file")
async def put_workspace_file_by_path(
    body: dict,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Write content to a file within the workspace directory."""
    path: str = body.get("path", "")
    content: str = body.get("content", "")
    if not path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing 'path'")
    workspace = Path(svc.config.agents.defaults.workspace).expanduser().resolve()
    target = (workspace / path).resolve()
    # Prevent path traversal
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Path outside workspace")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"name": target.name, "path": path, "content": content}


@router.delete("/workspace/file")
async def delete_workspace_file(
    path: str,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Delete a file or directory within the workspace."""
    if not path:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing 'path'")
    workspace = Path(svc.config.agents.defaults.workspace).expanduser().resolve()
    target = (workspace / path).resolve()
    # Prevent path traversal
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Path outside workspace")
    if not target.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Not found: {path}")
    # Protect core workspace files
    if target.name in _WORKSPACE_FILES and target.parent == workspace:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Cannot delete protected file: {target.name}")
    # Protect memory directory and its contents
    memory_dir = workspace / "memory"
    if target == memory_dir or str(target).startswith(str(memory_dir) + "/"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete memory files")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "path": path}


@router.get("/workspace/export")
async def export_workspace(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> StreamingResponse:
    """Package the entire .nanobot directory as a ZIP for download."""
    from nanobot.config.loader import get_config_path

    nanobot_dir = get_config_path().parent
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if nanobot_dir.exists():
            for f in sorted(nanobot_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(nanobot_dir))
    buf.seek(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"openjarvis_backup_{ts}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/workspace/import")
async def import_workspace(
    file: Annotated[UploadFile, File()],
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Import a .nanobot backup ZIP. Auto-backs up the current .nanobot dir first."""
    from nanobot.config.loader import get_config_path

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .zip files are accepted")

    nanobot_dir = get_config_path().parent
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path: str | None = None

    # Back up the current .nanobot directory before overwriting
    if nanobot_dir.exists() and any(nanobot_dir.iterdir()):
        backup_dir = nanobot_dir.parent / f".openjarvis_backup_{ts}"
        shutil.copytree(nanobot_dir, backup_dir)
        backup_path = str(backup_dir)

    # Extract the uploaded zip
    data = await file.read()
    buf = io.BytesIO(data)
    nanobot_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(buf, "r") as zf:
        # Security: reject paths that escape the target directory
        for member in zf.namelist():
            target = (nanobot_dir / member).resolve()
            if not str(target).startswith(str(nanobot_dir.resolve())):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Invalid path in archive: {member}",
                )
        zf.extractall(nanobot_dir)

    return {"ok": True, "backup": backup_path}


@router.get("/raw")
async def get_raw_config(
    _admin: Annotated[dict, Depends(require_admin)],
    _svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Return the raw config.json content as a string."""
    from nanobot.config.loader import get_config_path

    path = get_config_path()
    if not path.exists():
        return {"content": "{}"}
    return {"content": path.read_text(encoding="utf-8")}


@router.put("/raw")
async def put_raw_config(
    body: dict,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Validate and write raw config.json content."""
    from nanobot.config.loader import get_config_path

    content: str = body.get("content", "")
    # Validate JSON syntax first
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid JSON: {exc}") from exc
    # Validate against schema
    try:
        new_config = Config.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Schema validation error: {exc}") from exc

    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    # Sync in-memory config so all other routes (e.g. channels) see the new values
    svc.config.__dict__.update(new_config.__dict__)

    return {"ok": True, "content": content}
