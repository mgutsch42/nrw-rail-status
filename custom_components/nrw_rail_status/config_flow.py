"""Config flow for NRW Rail Status integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NRW Rail Status."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""

        # Nur eine Instanz erlauben
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Wenn der User bestätigt → Entry erstellen
        if user_input is not None:
            return self.async_create_entry(
                title="NRW Rail Status",
                data={},
            )

        # Leeres Formular anzeigen
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )
