"""Config flow for NRW Rail Status integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, NRW_LINES


class NRWRailStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NRW Rail Status."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step when adding the integration."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="NRW Rail Status", data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NRWRailStatusOptionsFlowHandler:
        """Get the options flow for this handler."""
        return NRWRailStatusOptionsFlowHandler()


class NRWRailStatusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for NRW Rail Status."""

    async def async_step_init(self, user_input=None):
        """Manage the options menu in HA."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # HA liest config_entry automatisch über self.config_entry
        selected_lines = self.config_entry.options.get("filtered_lines", [])

        schema = vol.Schema(
            {
                vol.Optional("filtered_lines", default=selected_lines): SelectSelector(
                    SelectSelectorConfig(
                        options=NRW_LINES,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
