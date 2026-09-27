"""Constants for NRW Rail Status / Zuginfo.nrw."""

from typing import Final

DOMAIN: Final = "nrw_rail_status"

# HAFAS Gateway URL von zuginfo.nrw
BASE_URL: Final = "https://www.zuginfo.nrw/vrr/mgate.exe"

# HAFAS Client-Konfiguration
HAFAS_AID: Final = "hafas-vrr-webapp"
HAFAS_VERSION: Final = "1.21"
HAFAS_LANG: Final = "de"
HAFAS_CLIENT_ID: Final = "VRR"
HAFAS_CLIENT_TYPE: Final = "WEB"
HAFAS_CLIENT_NAME: Final = "webapp"
HAFAS_CLIENT_LABEL: Final = "web"
HAFAS_CLIENT_VERSION: Final = "1.0.0"
HAFAS_EXT: Final = "VRR.1"

# Konfigurations-Schlüssel
CONF_LINES: Final = "filtered_lines"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"
DEFAULT_REFRESH_INTERVAL: Final = 15  # Minuten

# Kategorie-Ausschluss Option Mapping
CATEGORY_EXCLUDE_OPTIONS: Final = {
    "elevator": "Aufzugs- & Rolltreppenstörungen",
    "construction": "Bauarbeiten & Fahrplanänderungen",
    "disruption": "Aktuelle Störungen & Ausfälle",
}

# Auswählbare NRW-Linien für die Integration
NRW_LINES: Final = [
    # Regional-Express (RE)
    "RE1",
    "RE2",
    "RE3",
    "RE4",
    "RE5",
    "RE6",
    "RE7",
    "RE8",
    "RE9",
    "RE10",
    "RE11",
    "RE12",
    "RE13",
    "RE14",
    "RE15",
    "RE16",
    "RE17",
    "RE18",
    "RE19",
    "RE22",
    "RE42",
    "RE44",
    "RE49",
    "RE57",
    # Regionalbahn (RB)
    "RB20",
    "RB21",
    "RB24",
    "RB25",
    "RB27",
    "RB30",
    "RB31",
    "RB32",
    "RB33",
    "RB34",
    "RB35",
    "RB36",
    "RB37",
    "RB38",
    "RB39",
    "RB40",
    "RB43",
    "RB46",
    "RB48",
    "RB50",
    "RB51",
    "RB52",
    "RB53",
    "RB54",
    "RB59",
    "RB61",
    "RB63",
    "RB64",
    "RB65",
    "RB66",
    "RB67",
    "RB68",
    "RB69",
    "RB71",
    "RB72",
    "RB73",
    "RB74",
    "RB75",
    "RB77",
    "RB84",
    "RB85",
    "RB89",
    "RB91",
    "RB92",
    "RB93",
    "RB95",
    # S-Bahnen
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "S11",
    "S12",
    "S19",
    "S28",
    "S68",
]

AVAILABLE_LINES: Final = NRW_LINES
