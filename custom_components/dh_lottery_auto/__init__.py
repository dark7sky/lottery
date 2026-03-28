from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_GAMES,
    DOMAIN,
    MAX_GAMES_PER_PURCHASE,
    MIN_GAMES_PER_PURCHASE,
    NAME,
    SERVICE_REQUEST_PURCHASE,
)
from .coordinator import DhLotteryCoordinator
from .service import async_request_purchase

PLATFORMS = ["sensor", "button"]
REQUEST_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_GAMES): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_GAMES_PER_PURCHASE, max=MAX_GAMES_PER_PURCHASE),
        )
    }
)


def _get_entry_container(hass: HomeAssistant) -> dict[str, DhLotteryCoordinator]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault("entries", {})


def _get_coordinator(hass: HomeAssistant) -> DhLotteryCoordinator | None:
    entries = _get_entry_container(hass)
    return next(iter(entries.values()), None)


async def async_setup(hass: HomeAssistant, config: Mapping[str, object]) -> bool:
    if not hass.services.has_service(DOMAIN, SERVICE_REQUEST_PURCHASE):

        async def handle_request_purchase(call: ServiceCall) -> None:
            coordinator = _get_coordinator(hass)
            if coordinator is None:
                raise ServiceValidationError(
                    f"{NAME} integration is not configured yet"
                )
            games = call.data.get(CONF_GAMES)
            await async_request_purchase(hass, coordinator, games)

        hass.services.async_register(
            DOMAIN,
            SERVICE_REQUEST_PURCHASE,
            handle_request_purchase,
            schema=REQUEST_SCHEMA,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DhLotteryCoordinator(hass, entry)
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()
    _get_entry_container(hass)[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    entries = _get_entry_container(hass)
    entries.pop(entry.entry_id, None)
    if not entries and hass.services.has_service(DOMAIN, SERVICE_REQUEST_PURCHASE):
        hass.services.async_remove(DOMAIN, SERVICE_REQUEST_PURCHASE)
        hass.data.get(DOMAIN, {}).pop("entries", None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
