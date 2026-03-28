from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DhLotteryCoordinator
from .entity import DhLotteryEntity
from .service import async_request_purchase


class RequestPurchaseButton(DhLotteryEntity, ButtonEntity):
    _attr_translation_key = "request_purchase"

    def __init__(self, coordinator: DhLotteryCoordinator) -> None:
        super().__init__(coordinator, "request_purchase")

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            data is not None
            and not data.is_missing
            and not data.is_stale
            and not data.running
        )

    async def async_press(self) -> None:
        await async_request_purchase(self.hass, self.coordinator)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities,
) -> None:
    coordinator: DhLotteryCoordinator = hass.data.setdefault(DOMAIN, {}).setdefault(
        "entries", {}
    )[entry.entry_id]
    async_add_entities([RequestPurchaseButton(coordinator)])
