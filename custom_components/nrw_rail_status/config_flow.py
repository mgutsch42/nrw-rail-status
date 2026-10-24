"""Config flow for NRW Rail Status integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CATEGORY_EXCLUDE_OPTIONS,
    CONF_EXCLUDED_CATEGORIES,
    CONF_LINES,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    MAX_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    NRW_LINES,
)


class NRWRailStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfiguration beim Hinzufuegen der Integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster Schritt beim Hinzufuegen."""
        if user_input is not None:
            return self.async_create_entry(
                title="NRW Rail Status",
                data={CONF_LINES: user_input.get(CONF_LINES, [])},
                options={
                    CONF_LINES: user_input.get(CONF_LINES, []),
                    CONF_EXCLUDED_CATEGORIES: user_input.get(
                        CONF_EXCLUDED_CATEGORIES, []
                    ),
                    CONF_REFRESH_INTERVAL: user_input.get(
                        CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema({}),
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Options-Flow bereitstellen."""
        return NRWRailStatusOptionsFlowHandler()

    @staticmethod
    def _build_schema(current: dict[str, Any]) -> vol.Schema:
        """Formular aus den aktuellen Werten bauen."""
        return vol.Schema(
            {
                vol.Optional(
                    CONF_LINES, default=current.get(CONF_LINES, [])
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=NRW_LINES,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_EXCLUDED_CATEGORIES,
                    default=current.get(CONF_EXCLUDED_CATEGORIES, []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in CATEGORY_EXCLUDE_OPTIONS.items()
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.CHECKBOXES,
                    )
                ),
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=current.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_REFRESH_INTERVAL,
                        max=MAX_REFRESH_INTERVAL,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )


class NRWRailStatusOptionsFlowHandler(config_entries.OptionsFlow):
    """Options-Flow.

    Arbeitet mit der von Home Assistant bereitgestellten Referenz
    ``self.config_entry``; ein eigenes Feld gleichen Namens wuerde in
    aktuellen HA-Versionen einen Fehler ausloesen.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optionen bearbeiten."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = dict(self.config_entry.options or {})
        if not current:
            current = dict(self.config_entry.data or {})

        return self.async_show_form(
            step_id="init",
            data_schema=NRWRailStatusConfigFlow._build_schema(current),
        )
