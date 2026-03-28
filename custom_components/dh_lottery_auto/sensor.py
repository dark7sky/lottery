from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DhLotteryCoordinator
from .entity import DhLotteryEntity
from .models import LotteryState


@dataclass(frozen=True, kw_only=True)
class DhLotterySensorDefinition:
    unique_id_suffix: str
    translation_key: str
    value_fn: Callable[[LotteryState], object]
    extra_fn: Callable[[LotteryState], dict[str, object]]
    device_class: SensorDeviceClass | None = None


SENSOR_DEFINITIONS: tuple[DhLotterySensorDefinition, ...] = (
    DhLotterySensorDefinition(
        unique_id_suffix="status",
        translation_key="status",
        value_fn=lambda state: state.status_label,
        extra_fn=lambda state: {
            "running": state.running,
            "is_missing": state.is_missing,
            "is_stale": state.is_stale,
            "configured_games_per_purchase": state.games_per_purchase,
            "configured_interval_days": state.interval_days,
            "last_error": state.last_error,
            "last_message": state.last_message,
            "last_run_at": DhLotteryEntity._format_datetime(state.last_run_at),
            "next_run_at": DhLotteryEntity._format_datetime(state.next_run_at),
        },
    ),
    DhLotterySensorDefinition(
        unique_id_suffix="last_result",
        translation_key="last_result",
        value_fn=lambda state: state.last_result,
        extra_fn=lambda state: {
            "last_message": state.last_message,
            "last_error": state.last_error,
            "last_balance": state.last_balance,
            "last_run_at": DhLotteryEntity._format_datetime(state.last_run_at),
            "last_success_at": DhLotteryEntity._format_datetime(state.last_success_at),
        },
    ),
    DhLotterySensorDefinition(
        unique_id_suffix="this_week_numbers",
        translation_key="this_week_numbers",
        value_fn=lambda state: state.weekly_summary,
        extra_fn=lambda state: {
            "games": state.weekly_games_count,
            "tickets": list(state.weekly_ticket_lines),
            "week_start": DhLotteryEntity._format_datetime(state.weekly_window[0]),
            "week_end": DhLotteryEntity._format_datetime(state.weekly_window[1]),
        },
    ),
    DhLotterySensorDefinition(
        unique_id_suffix="next_run",
        translation_key="next_run",
        value_fn=lambda state: state.next_run_at,
        extra_fn=lambda state: {
            "state_age_seconds": state.state_age_seconds,
            "load_error": state.load_error,
        },
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


class DhLotterySensor(DhLotteryEntity, SensorEntity):
    def __init__(
        self,
        coordinator: DhLotteryCoordinator,
        definition: DhLotterySensorDefinition,
    ) -> None:
        super().__init__(coordinator, definition.unique_id_suffix)
        self._definition = definition
        self._attr_translation_key = definition.translation_key
        self._attr_device_class = definition.device_class

    @property
    def native_value(self):
        return self._definition.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        return self._definition.extra_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities,
) -> None:
    coordinator: DhLotteryCoordinator = hass.data.setdefault(DOMAIN, {}).setdefault(
        "entries", {}
    )[entry.entry_id]
    async_add_entities([DhLotterySensor(coordinator, definition) for definition in SENSOR_DEFINITIONS])
