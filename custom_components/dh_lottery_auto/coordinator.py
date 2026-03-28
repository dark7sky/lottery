from __future__ import annotations

from functools import partial
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_GAMES_PER_PURCHASE,
    DEFAULT_INTERVAL_DAYS,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .models import LotteryState
from .notifier import DhLotteryNotifier

_LOGGER = logging.getLogger(__name__)


class DhLotteryCoordinator(DataUpdateCoordinator[LotteryState]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._data_dir = Path(hass.config.path("dh_lottery_auto"))
        self._state_path = self._data_dir / "state.json"
        self._notifier = DhLotteryNotifier(hass, config_entry)
        self._has_loaded_once = False
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN} state",
            update_interval=UPDATE_INTERVAL,
        )

    async def async_initialize(self) -> None:
        await self._notifier.async_initialize()

    @property
    def state_path(self) -> Path:
        return self._state_path

    @property
    def request_games(self) -> int:
        if self.data is not None:
            return self.data.games_per_purchase or DEFAULT_GAMES_PER_PURCHASE
        return DEFAULT_GAMES_PER_PURCHASE

    @property
    def configured_games_per_purchase(self) -> int:
        return self.request_games

    @property
    def configured_interval_days(self) -> int:
        if self.data is not None:
            return self.data.interval_days or DEFAULT_INTERVAL_DAYS
        return DEFAULT_INTERVAL_DAYS

    async def _async_update_data(self) -> LotteryState:
        try:
            state = await self.hass.async_add_executor_job(
                partial(
                    LotteryState.from_path,
                    self.state_path,
                    games_per_purchase=self.request_games or 5,
                    interval_days=self.configured_interval_days or 7,
                )
            )
            await self._notifier.async_process_state(
                state, is_initial_refresh=not self._has_loaded_once
            )
            self._has_loaded_once = True
            return state
        except Exception as exc:  # pragma: no cover - coordinator safety net
            raise UpdateFailed(str(exc)) from exc
