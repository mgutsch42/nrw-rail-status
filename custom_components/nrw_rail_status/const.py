"""Constants for the NRW Rail Status integration."""

DOMAIN = "nrw_rail_status"

# Update interval in seconds
DEFAULT_UPDATE_INTERVAL = 60
CONF_SCAN_INTERVAL = "scan_interval"

# Sensor name
SENSOR_NAME = "NRW Rail Status"
ATTRIBUTION = "Data provided by zuginfo.nrw"

# -----------------------------
# HAFAS / Zuginfo API constants
# -----------------------------

# Base URL for the Zuginfo NRW gateway
BASE_URL = "https://www.zuginfo.nrw/gate/"
MAIN_URL = "https://www.zuginfo.nrw/"

# HAFAS API version
HAFAS_VERSION = "1.24"

# Client information (must match the webapp)
HAFAS_CLIENT_ID = "HAFAS"
HAFAS_CLIENT_TYPE = "WEB"
HAFAS_CLIENT_NAME = "webapp"
HAFAS_CLIENT_LABEL = "vs_webapp"
HAFAS_CLIENT_VERSION = 10107

# Authentication (AID key)
HAFAS_AID = "23lkjh63l456oisplergn"

# Namespace / extension (VRR-specific)
HAFAS_EXT = "VRR.1"

# Default language (HAFAS uses "deu", not "de")
HAFAS_LANG = "deu"

# -----------------------------
# NRW Rail Lines Filter
# -----------------------------

# Exakte Linienbezeichnungen von zuginfo.nrw für das Options-Dropdown
NRW_LINES = [
    "RE 1 (RRX)",
    "RE 2",
    "RE 3",
    "RE 4",
    "RE 5 (RRX)",
    "RE 6 (RRX)",
    "RE 7",
    "RE 8",
    "RE 9",
    "RE 10",
    "RE 11 (RRX)",
    "RE 12",
    "RE 13",
    "RE 14",
    "RE 15",
    "RE 16",
    "RE 17",
    "RE 18",
    "RE 19",
    "RE 22",
    "RE 34",
    "RE 41",
    "RE 42",
    "RE 44",
    "RE 47",
    "RE 49",
    "RE 57",
    "RE 60",
    "RE 70",
    "RE 78",
    "RE 82",
    "RB 20",
    "RB 21 Nord",
    "RB 21 Süd",
    "RB 22",
    "RB 24",
    "RB 25",
    "RB 26",
    "RB 27",
    "RB 28",
    "RB 28 (RLP)",
    "RB 30",
    "RB 31",
    "RB 32",
    "RB 33",
    "RB 34",
    "RB 35",
    "RB 36",
    "RB 37",
    "RB 38",
    "RB 39",
    "RB 39 (RLP)",
    "RB 40",
    "RB 43",
    "RB 46",
    "RB 48",
    "RB 50",
    "RB 51",
    "RB 52",
    "RB 53",
    "RB 54",
    "RB 59",
    "RB 61",
    "RB 63",
    "RB 64",
    "RB 65",
    "RB 66",
    "RB 67",
    "RB 69",
    "RB 71",
    "RB 72",
    "RB 73",
    "RB 74",
    "RB 75",
    "RB 84",
    "RB 85",
    "RB 89",
    "RB 91",
    "S 1",
    "S 2",
    "S 3",
    "S 4",
    "S 5",
    "S 6",
    "S 7",
    "S 8",
    "S 9",
    "S 11",
    "S 12",
    "S 19",
    "S 23",
    "S 28",
    "S 41",
    "S 68",
]
