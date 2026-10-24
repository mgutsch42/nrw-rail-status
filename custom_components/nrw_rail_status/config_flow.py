"""Config flow for NRW Rail Status integration.

Bewusst ohne SelectSelectorMode und NumberSelectorMode: Diese Konstanten
haengen von der Home-Assistant-Version ab. Stattdessen werden die klassischen
Voluptuous-Typen benutzt, die in jeder Version verfuegbar sind:

  * cv.multi_select({...})  -> Mehrfachauswahl als Kaestchen/Dropdown
  * vol.All(vol.Coerce(int), vol.Range(...)) -> Zahleneingabe mit Grenzen

Damit laesst sich das Formular in jeder HA-Version laden.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

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


def _build_schema(current: dict[str, Any]) -> vol.Schema:
    """Formular aus den aktuellen Werten bauen."""
    # Linienliste als Auswahl: Schluessel und Anzeigetext sind hier identisch.
    lines = {name: name for name in NRW_LINES}

    # Kategorien: Schluessel ist die Ziffer, angezeigt wird der Klartext.
    cats = {key: label for key, label in CATEGORY_EXCLUDE_OPTIONS.items()}

    return vol.Schema(
        {
            vol.Optional(
                CONF_LINES, default=current.get(CONF_LINES, [])
            ): cv.multi_select(lines),
            vol.Optional(
                CONF_EXCLUDED_CATEGORIES,
                default=current.get(CONF_EXCLUDED_CATEGORIES, []),
            ): cv.multi_select(cats),
            vol.Optional(
                CONF_REFRESH_INTERVAL,
                default=current.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
            ),
        }
    )


class NRWRailStatusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Konfiguration beim Hinzufuegen der Integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster Schritt beim Hinzufuegen."""
        if user_input is not None:
            lines = user_input.get(CONF_LINES, [])
            return self.async_create_entry(
                title="NRW Rail Status",
                data={CONF_LINES: lines},
                options={
                    CONF_LINES: lines,
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
            data_schema=_build_schema({}),
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Options-Flow bereitstellen."""
        return NRWRailStatusOptionsFlowHandler()


class NRWRailStatusOptionsFlowHandler(config_entries.OptionsFlow):
    """Options-Flow.

    Nutzt die von Home Assistant bereitgestellte Referenz ``self.config_entry``;
    ein eigenes Feld gleichen Namens wuerde in aktuellen Versionen einen Fehler
    ausloesen.
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
            data_schema=_build_schema(current),
        )
