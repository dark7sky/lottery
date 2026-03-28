from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFY_ENTITY_ID,
    DOMAIN,
    NAME,
    NOTIFICATION_MODE_NONE,
    NOTIFICATION_MODE_NOTIFY_ENTITY,
    NOTIFICATION_MODE_PERSISTENT,
)


def _mode_schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NOTIFICATION_MODE,
                default=defaults.get(CONF_NOTIFICATION_MODE, NOTIFICATION_MODE_NONE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {
                            "value": NOTIFICATION_MODE_NONE,
                            "label": "No Home Assistant notification",
                        },
                        {
                            "value": NOTIFICATION_MODE_PERSISTENT,
                            "label": "Persistent notification",
                        },
                        {
                            "value": NOTIFICATION_MODE_NOTIFY_ENTITY,
                            "label": "Notify entity",
                        },
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _notify_entity_schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_NOTIFY_ENTITY_ID,
                default=defaults.get(CONF_NOTIFY_ENTITY_ID, ""),
            ): EntitySelector(EntitySelectorConfig(domain="notify"))
        }
    )


class DhLotteryAutoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _pending_input: dict

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DhLotteryAutoOptionsFlow()

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            self._pending_input = dict(user_input)
            if user_input[CONF_NOTIFICATION_MODE] == NOTIFICATION_MODE_NOTIFY_ENTITY:
                return await self.async_step_notify_entity()
            return self.async_create_entry(title=NAME, data=self._pending_input)
        return self.async_show_form(step_id="user", data_schema=_mode_schema())

    async def async_step_notify_entity(self, user_input=None):
        if user_input is not None:
            data = {**self._pending_input, **user_input}
            return self.async_create_entry(title=NAME, data=data)
        return self.async_show_form(
            step_id="notify_entity",
            data_schema=_notify_entity_schema(self._pending_input),
        )


class DhLotteryAutoOptionsFlow(config_entries.OptionsFlow):
    _pending_input: dict

    async def async_step_init(self, user_input=None):
        defaults = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            self._pending_input = dict(user_input)
            if user_input[CONF_NOTIFICATION_MODE] == NOTIFICATION_MODE_NOTIFY_ENTITY:
                return await self.async_step_notify_entity()
            return self.async_create_entry(title="", data=self._pending_input)
        return self.async_show_form(step_id="init", data_schema=_mode_schema(defaults))

    async def async_step_notify_entity(self, user_input=None):
        defaults = {**self.config_entry.data, **self.config_entry.options, **self._pending_input}
        if user_input is not None:
            data = {**self._pending_input, **user_input}
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(
            step_id="notify_entity",
            data_schema=_notify_entity_schema(defaults),
        )
