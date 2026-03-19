"""File upload/download route – stores files locally in ~/.nanobot/uploads/."""

from __future__ import annotations

import uuid
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request

from server.api.deps import get_current_user

def get_uploads_path(request: Request) -> Path:
    return request.app.state.uploads_dir

router = APIRouter()


from fastapi.responses import FileResponse

@router.post("/upload")
async def upload_file(
    _user: Annotated[dict, Depends(get_current_user)],
    uploads_path: Annotated[Path, Depends(get_uploads_path)],
    file: UploadFile = File(...),
):
    uploads_path.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix
    name = f"{uuid.uuid4().hex}{ext}"
    dest = uploads_path / name
    content = await file.read()
    dest.write_bytes(content)
    return {"url": f"/api/files/{name}"}


@router.get("/{name}")
async def get_file(
    name: str,
    uploads_path: Annotated[Path, Depends(get_uploads_path)],
):
    path = uploads_path / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), filename=name)
