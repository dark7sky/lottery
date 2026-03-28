from __future__ import annotations

import uuid
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_GAMES,
    DOMAIN,
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
)
from .coordinator import DhLotteryCoordinator
from .storage import (
    get_processing_request_path,
    get_request_path,
    write_json_atomic,
)


def _request_payload(games: int | None) -> dict:
    payload = {
        "request_id": str(uuid.uuid4()),
        "requested_at": datetime.now().astimezone().isoformat(),
        "source": DOMAIN,
    }
    if games is not None:
        payload[CONF_GAMES] = int(games)
    return payload


async def async_request_purchase(
    hass: HomeAssistant,
    coordinator: DhLotteryCoordinator | None,
    games: int | None = None,
) -> str:
    if coordinator is None:
        raise ServiceValidationError("DH Lottery Auto integration is not configured")
    if coordinator.data is None or coordinator.data.is_missing:
        raise ServiceValidationError("Add-on state file is missing")
    if coordinator.data.is_stale:
        raise ServiceValidationError("Add-on state is stale")
    if coordinator.data.running:
        raise ServiceValidationError("A purchase is already in progress")

    if games is None and coordinator is not None:
        games = coordinator.request_games
    if games is not None and not MIN_GAMES_PER_PURCHASE <= int(games) <= MAX_GAMES_PER_PURCHASE:
        raise ServiceValidationError(
            f"Games must be between {MIN_GAMES_PER_PURCHASE} and {MAX_GAMES_PER_PURCHASE}"
        )

    request_path = get_request_path(hass)
    processing_request_path = get_processing_request_path(hass)
    if request_path.exists() or processing_request_path.exists():
        raise ServiceValidationError("A purchase request is already pending")

    payload = _request_payload(games)
    await hass.async_add_executor_job(write_json_atomic, request_path, payload)
    return str(payload["request_id"])
