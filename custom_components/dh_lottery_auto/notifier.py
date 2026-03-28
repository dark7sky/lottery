from __future__ import annotations

import logging

from homeassistant.components.persistent_notification import async_create as async_create_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFY_ENTITY_ID,
    DOMAIN,
    NOTIFICATION_MODE_NONE,
    NOTIFICATION_MODE_NOTIFY_ENTITY,
    NOTIFICATION_MODE_PERSISTENT,
    NOTIFIER_STORAGE_VERSION,
)
from .models import LotteryState, PurchaseAttempt, STATUS_FAILURE, STATUS_INSUFFICIENT_BALANCE, STATUS_SUCCESS

_LOGGER = logging.getLogger(__name__)


def _merge_entry_config(entry: ConfigEntry) -> dict:
    return {**entry.data, **entry.options}


def _latest_completed_attempt(state: LotteryState) -> PurchaseAttempt | None:
    for attempt in state.history:
        if attempt.finished_at is not None:
            return attempt
    return None


def _attempt_key(attempt: PurchaseAttempt) -> str:
    finished_at = attempt.finished_at.isoformat() if attempt.finished_at else "pending"
    return f"{attempt.request_id}:{finished_at}:{attempt.status}"


def _notification_title(attempt: PurchaseAttempt) -> str:
    if attempt.status == STATUS_SUCCESS:
        return "DH Lottery Auto 구매 성공"
    if attempt.status == STATUS_INSUFFICIENT_BALANCE:
        return "DH Lottery Auto 잔액 부족"
    if attempt.status == STATUS_FAILURE:
        return "DH Lottery Auto 구매 실패"
    return "DH Lottery Auto 알림"


def _notification_message(attempt: PurchaseAttempt) -> str:
    trigger_label = "수동 실행" if attempt.trigger == "manual" else "예약 실행"
    lines = [f"[{trigger_label}] {attempt.message}"]
    if attempt.balance is not None:
        lines.append(f"잔액: {attempt.balance:,}원")
    if attempt.ticket_lines:
        lines.append("")
        lines.extend(attempt.ticket_lines)
    if attempt.error and attempt.error not in attempt.message:
        lines.append("")
        lines.append(f"오류: {attempt.error}")
    return "\n".join(lines)


class DhLotteryNotifier:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self._store = Store(
            hass,
            NOTIFIER_STORAGE_VERSION,
            f"{DOMAIN}_notifier_{config_entry.entry_id}",
        )
        self._last_notified_key: str | None = None

    async def async_initialize(self) -> None:
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self._last_notified_key = stored.get("last_notified_key")

    async def async_process_state(self, state: LotteryState, is_initial_refresh: bool) -> None:
        attempt = _latest_completed_attempt(state)
        if attempt is None:
            return

        current_key = _attempt_key(attempt)
        if self._last_notified_key == current_key:
            return

        if is_initial_refresh and self._last_notified_key is None:
            await self._async_set_last_notified_key(current_key)
            return

        try:
            await self._async_send_notification(attempt)
        except Exception:
            _LOGGER.exception("Failed to send Home Assistant notification")
            return
        await self._async_set_last_notified_key(current_key)

    async def _async_set_last_notified_key(self, key: str) -> None:
        self._last_notified_key = key
        await self._store.async_save({"last_notified_key": key})

    async def _async_send_notification(self, attempt: PurchaseAttempt) -> None:
        merged = _merge_entry_config(self.config_entry)
        mode = merged.get(CONF_NOTIFICATION_MODE, NOTIFICATION_MODE_NONE)
        if mode == NOTIFICATION_MODE_NONE:
            return

        title = _notification_title(attempt)
        message = _notification_message(attempt)

        if mode == NOTIFICATION_MODE_PERSISTENT:
            async_create_notification(
                self.hass,
                message=message,
                title=title,
                notification_id=f"{DOMAIN}_{attempt.request_id}",
            )
            return

        if mode == NOTIFICATION_MODE_NOTIFY_ENTITY:
            entity_id = merged.get(CONF_NOTIFY_ENTITY_ID)
            if not entity_id:
                _LOGGER.warning("Notification mode is notify_entity but no entity is configured")
                return
            await self.hass.services.async_call(
                "notify",
                "send_message",
                {
                    "message": message,
                    "title": title,
                    "entity_id": entity_id,
                },
                blocking=True,
            )
            return

        _LOGGER.warning("Unknown notification mode configured: %s", mode)
