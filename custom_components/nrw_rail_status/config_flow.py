"""Config flow for NRW Rail Status integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = 60


class NRWRailStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NRW Rail Status."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id("nrw_rail_status")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="NRW Rail Status",
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return NRWRailStatusOptionsFlowHandler()


class NRWRailStatusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for NRW Rail Status."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            "scan_interval",
            self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("scan_interval", default=current_interval): int,
                }
            ),
        )
