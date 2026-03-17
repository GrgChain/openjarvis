"""Cron jobs routes (CRUD)."""

from __future__ import annotations

import datetime
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from server.api.deps import get_services, require_admin
from server.api.gateway import ServiceContainer
from server.api.models import CronJobInfo, CronJobRequest, CronScheduleModel, CronStateModel, CronPayloadModel

router = APIRouter()


def _sync_heartbeat_file(svc: ServiceContainer) -> None:
    """Regenerate HEARTBEAT.md Active Tasks section from current cron jobs.

    Called after every cron CRUD operation so the heartbeat service
    sees up-to-date task data without modifying any nanobot source files.
    """
    jobs = svc.cron.list_jobs(include_disabled=True)
    hb_path = svc.config.workspace_path / "HEARTBEAT.md"

    lines = [
        "# Heartbeat Tasks",
        "",
        "This file is automatically synced with cron jobs.",
        "",
        "## Active Tasks",
        "",
    ]

    enabled_jobs = [j for j in jobs if j.enabled]
    disabled_jobs = [j for j in jobs if not j.enabled]

    if enabled_jobs:
        for j in enabled_jobs:
            sched = j.schedule
            if sched.kind == "cron" and sched.expr:
                sched_str = f"cron `{sched.expr}`"
            elif sched.kind == "interval" and sched.every_ms:
                mins = sched.every_ms // 60_000
                sched_str = f"every {mins}m" if mins else f"every {sched.every_ms}ms"
            elif sched.kind == "once" and sched.at_ms:
                dt = datetime.datetime.fromtimestamp(sched.at_ms / 1000)
                sched_str = f"once at {dt:%Y-%m-%d %H:%M}"
            else:
                sched_str = sched.kind

            status_str = ""
            if j.state.last_status:
                status_str = f" (last: {j.state.last_status})"
            if j.state.next_run_at_ms:
                next_dt = datetime.datetime.fromtimestamp(j.state.next_run_at_ms / 1000)
                status_str += f" → next: {next_dt:%Y-%m-%d %H:%M}"

            lines.append(f"- **{j.name}** [{sched_str}]{status_str}")
            lines.append(f"  - {j.payload.message}")
    else:
        lines.append("<!-- No active cron jobs -->")

    lines.append("")

    if disabled_jobs:
        lines.append("## Disabled")
        lines.append("")
        for j in disabled_jobs:
            lines.append(f"- ~~{j.name}~~ — {j.payload.message}")
        lines.append("")

    lines.append("## Completed")
    lines.append("")
    lines.append("<!-- Move completed tasks here or delete them -->")
    lines.append("")

    try:
        hb_path.parent.mkdir(parents=True, exist_ok=True)
        hb_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        logger.exception("Failed to sync HEARTBEAT.md")


def _to_info(job) -> CronJobInfo:
    return CronJobInfo(
        id=job.id,
        name=job.name,
        enabled=job.enabled,
        schedule=CronScheduleModel(
            kind=job.schedule.kind,
            at_ms=job.schedule.at_ms,
            every_ms=job.schedule.every_ms,
            expr=job.schedule.expr,
            tz=job.schedule.tz,
        ),
        payload=CronPayloadModel(
            message=job.payload.message,
            deliver=job.payload.deliver,
            channel=job.payload.channel,
            to=job.payload.to,
        ),
        state=CronStateModel(
            next_run_at_ms=job.state.next_run_at_ms,
            last_run_at_ms=job.state.last_run_at_ms,
            last_status=job.state.last_status,
            last_error=job.state.last_error,
        ),
        delete_after_run=job.delete_after_run,
        created_at_ms=job.created_at_ms,
        updated_at_ms=job.updated_at_ms,
    )


@router.get("/jobs", response_model=list[CronJobInfo])
async def list_jobs(
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> list[CronJobInfo]:
    return [_to_info(j) for j in svc.cron.list_jobs(include_disabled=True)]


@router.post("/jobs", response_model=CronJobInfo, status_code=201)
async def create_job(
    body: CronJobRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> CronJobInfo:
    from nanobot.cron.types import CronSchedule

    try:
        job = svc.cron.add_job(
            name=body.name,
            schedule=CronSchedule(
                kind=body.schedule.kind,
                at_ms=body.schedule.at_ms,
                every_ms=body.schedule.every_ms,
                expr=body.schedule.expr,
                tz=body.schedule.tz,
            ),
            message=body.payload.message,
            deliver=body.payload.deliver,
            channel=body.payload.channel,
            to=body.payload.to,
            delete_after_run=body.delete_after_run,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    if not body.enabled:
        svc.cron.enable_job(job.id, False)
        job = next((j for j in svc.cron.list_jobs(include_disabled=True) if j.id == job.id), job)

    _sync_heartbeat_file(svc)
    return _to_info(job)


@router.put("/jobs/{job_id}", response_model=CronJobInfo)
async def update_job(
    job_id: str,
    body: CronJobRequest,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> CronJobInfo:
    """Update a job by replacing schedule/payload in-place via store access."""
    from nanobot.cron.types import CronPayload, CronSchedule

    store = svc.cron._load_store()
    job = next((j for j in store.jobs if j.id == job_id), None)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job '{job_id}' not found")

    job.name = body.name
    job.enabled = body.enabled
    job.delete_after_run = body.delete_after_run
    job.schedule = CronSchedule(
        kind=body.schedule.kind,
        at_ms=body.schedule.at_ms,
        every_ms=body.schedule.every_ms,
        expr=body.schedule.expr,
        tz=body.schedule.tz,
    )
    job.payload = CronPayload(
        kind="agent_turn",
        message=body.payload.message,
        deliver=body.payload.deliver,
        channel=body.payload.channel,
        to=body.payload.to,
    )
    job.updated_at_ms = int(time.time() * 1000)

    # Recompute next run
    from nanobot.cron.service import _compute_next_run
    if job.enabled:
        job.state.next_run_at_ms = _compute_next_run(job.schedule, int(time.time() * 1000))
    else:
        job.state.next_run_at_ms = None

    svc.cron._save_store()
    svc.cron._arm_timer()
    _sync_heartbeat_file(svc)
    return _to_info(job)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    _admin: Annotated[dict, Depends(require_admin)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> None:
    removed = svc.cron.remove_job(job_id)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job '{job_id}' not found")
    _sync_heartbeat_file(svc)
