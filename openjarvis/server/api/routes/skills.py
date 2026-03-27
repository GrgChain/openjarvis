"""Skills routes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated
import zipfile
import io

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from server.api.deps import get_services, get_current_user, require_admin
from server.api.gateway import ServiceContainer
from server.api.models import (
    CreateSkillRequest,
    SkillContent,
    SkillInfo,
    UpdateSkillRequest,
)

router = APIRouter()

_BUILTIN_SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "nanobot" / "skills"
_DISABLED_SKILLS_FILE = ".disabled_skills.json"


def _load_disabled(workspace: Path) -> set[str]:
    p = workspace / _DISABLED_SKILLS_FILE
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save_disabled(workspace: Path, disabled: set[str]) -> None:
    p = workspace / _DISABLED_SKILLS_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(disabled), ensure_ascii=False), encoding="utf-8")


def _skill_available(name: str, path: str) -> tuple[bool, str | None]:
    """Check whether a skill's external binary requirements are met."""
    skill_path = Path(path)
    if not skill_path.exists():
        return False, "SKILL.md not found"
    content = skill_path.read_text(encoding="utf-8")
    # Look for "## Requirements" section with `command: <bin>` lines
    for line in content.splitlines():
        m = re.match(r"^\s*-?\s*`?([a-zA-Z0-9_-]+)`?\s*(?:binary|command|bin|cli)", line, re.I)
        if m:
            import shutil
            bin_name = m.group(1)
            if not shutil.which(bin_name):
                return False, f"binary `{bin_name}` not found in PATH"
    return True, None


@router.get("", response_model=list[SkillInfo])
async def list_skills(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> list[SkillInfo]:
    from nanobot.agent.skills import SkillsLoader

    loader = SkillsLoader(svc.config.workspace_path)
    all_skills = loader.list_skills(filter_unavailable=False)
    disabled = _load_disabled(svc.config.workspace_path)
    result = []
    for s in all_skills:
        available, reason = _skill_available(s["name"], s["path"])
        description = loader._get_skill_description(s["name"])
        skill_meta = loader._get_skill_meta(s["name"])
        emoji = skill_meta.get("emoji", "")
        result.append(
            SkillInfo(
                name=s["name"],
                source=s["source"],
                path=s["path"],
                description=description,
                emoji=emoji,
                available=available,
                enabled=s["name"] not in disabled,
                unavailable_reason=reason,
            )
        )
    return result


@router.get("/{name}", response_model=SkillContent)
async def get_skill(
    name: str,
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> SkillContent:
    from nanobot.agent.skills import SkillsLoader

    loader = SkillsLoader(svc.config.workspace_path)
    all_skills = loader.list_skills(filter_unavailable=False)
    skill = next((s for s in all_skills if s["name"] == name), None)
    if not skill:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Skill '{name}' not found")

    content = Path(skill["path"]).read_text(encoding="utf-8")
    return SkillContent(name=name, source=skill["source"], content=content)


@router.post("", response_model=SkillContent, status_code=201)
async def create_skill(
    body: CreateSkillRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> SkillContent:
    skill_dir = svc.config.workspace_path / "skills" / body.name
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Skill '{body.name}' already exists")

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(body.content, encoding="utf-8")
    return SkillContent(name=body.name, source="workspace", content=body.content)


@router.put("/{name}", response_model=SkillContent)
async def update_skill(
    name: str,
    body: UpdateSkillRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> SkillContent:
    skill_file = svc.config.workspace_path / "skills" / name / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Custom skill '{name}' not found")

    skill_file.write_text(body.content, encoding="utf-8")
    return SkillContent(name=name, source="workspace", content=body.content)


@router.delete("/{name}", status_code=204)
async def delete_skill(
    name: str,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> None:
    import shutil

    skill_dir = svc.config.workspace_path / "skills" / name
    if not skill_dir.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Custom skill '{name}' not found")

    shutil.rmtree(skill_dir)


@router.post("/{name}/toggle")
async def toggle_skill(
    name: str,
    body: dict,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Enable or disable a skill (persisted in workspace)."""

    enabled: bool = bool(body.get("enabled", True))
    workspace = svc.config.workspace_path
    disabled = _load_disabled(workspace)

    if enabled:
        disabled.discard(name)
    else:
        disabled.add(name)

    _save_disabled(workspace, disabled)
    return {"name": name, "enabled": enabled}


@router.post("/upload", status_code=201)
async def upload_skill(
    file: Annotated[UploadFile, File()],
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict:
    """Upload a skill from a ZIP file."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .zip files are allowed")

    content = await file.read()
    workspace_skills_dir = svc.config.workspace_path / "skills"

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Check for SKILL.md
            infolist = zf.infolist()
            skill_md_path = next((info.filename for info in infolist if info.filename.endswith("SKILL.md") and not info.is_dir()), None)

            if not skill_md_path:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded ZIP does not contain SKILL.md")

            # Determine the skill name. If SKILL.md is inside a single root folder, use that folder name.
            # Otherwise, use the zip filename minus .zip
            parts = Path(skill_md_path).parts
            if len(parts) > 1 and all(Path(info.filename).parts[0] == parts[0] for info in infolist if info.filename):
                skill_name = parts[0]
                has_root_dir = True
            else:
                skill_name = file.filename[:-4]
                has_root_dir = False

            if not skill_name:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid skill name")

            target_dir = workspace_skills_dir / skill_name
            if target_dir.exists():
                raise HTTPException(status.HTTP_409_CONFLICT, f"Skill '{skill_name}' already exists")

            target_dir.mkdir(parents=True, exist_ok=True)

            # Extract files
            for info in infolist:
                if info.is_dir():
                    continue
                # If everything was wrapped in a root dir, strip it for extraction (or just preserve structure)
                # It's safer to extract everything. The SKILL.md will be at `target_dir / (skill_md_path minus root_dir if stripped)`
                # Let's just extract all contents inside target_dir. If there is a root dir, extract into workspace_skills_dir directly?
                # No, if there is a root dir, it means the structure is already `skill_name/SKILL.md`.
                # So if we extract it into `workspace_skills_dir`, it will create `workspace_skills_dir/skill_name/SKILL.md`.
                pass

            if has_root_dir:
                zf.extractall(path=workspace_skills_dir)
            else:
                zf.extractall(path=target_dir)

    except zipfile.BadZipFile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ZIP file")

    return {"name": skill_name, "message": "Uploaded successfully"}
