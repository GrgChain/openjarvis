"""Dashboard stats route — accessible to all authenticated users."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from server.api.deps import get_current_user, get_services
from server.api.gateway import ServiceContainer
from server.api.models import ChannelSummary, DashboardStatsResponse

router = APIRouter()

_CHANNEL_NAMES = [
    "telegram", "whatsapp", "discord", "feishu", "dingtalk",
    "email", "slack", "qq", "matrix", "mochat",
]


def _get_enabled(ch_cfg: Any) -> bool:
    if isinstance(ch_cfg, dict):
        return ch_cfg.get("enabled", True)
    return getattr(ch_cfg, "enabled", True)


@router.get("/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> DashboardStatsResponse:
    status_map = svc.channels.get_status()

    channels: list[ChannelSummary] = []
    for name in _CHANNEL_NAMES:
        ch_cfg = getattr(svc.config.channels, name, None)
        if ch_cfg is None:
            continue
        running_info = status_map.get(name, {})
        channels.append(
            ChannelSummary(
                name=name,
                enabled=_get_enabled(ch_cfg),
                running=running_info.get("running", False),
                error=running_info.get("error"),
            )
        )

    running_channels = sum(1 for c in channels if c.running)

    all_jobs = svc.cron.list_jobs(include_disabled=True)
    enabled_cron = sum(1 for j in all_jobs if j.enabled)

    return DashboardStatsResponse(
        channels=channels,
        running_channels=running_channels,
        total_channels=len(channels),
        enabled_cron=enabled_cron,
        total_cron=len(all_jobs),
    )
