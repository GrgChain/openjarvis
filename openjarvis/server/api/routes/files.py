"""File upload/download route – stores files locally in ~/.nanobot/uploads/."""

from __future__ import annotations

import uuid
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from server.api.deps import get_current_user

UPLOADS_DIR = Path.home() / ".nanobot" / "uploads"

router = APIRouter()


@router.post("/upload")
async def upload_file(
    _user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix
    name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / name
    content = await file.read()
    dest.write_bytes(content)
    return {"url": f"/api/files/{name}"}


@router.get("/{name}")
async def get_file(name: str):
    path = UPLOADS_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=name)
