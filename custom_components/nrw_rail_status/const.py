"""Constants for NRW Rail Status integration."""

DOMAIN = "nrw_rail_status"
DEFAULT_UPDATE_INTERVAL = 300

# Offizielle Schnittstellen-URL von zuginfo.nrw für ganz NRW
MAIN_URL = "https://www.zuginfo.nrw/"
BASE_URL = "https://www.zuginfo.nrw/vrr/mgate.exe"

HAFAS_VERSION = "1.58"
HAFAS_LANG = "deu"
HAFAS_AID = "N93315721115312"
HAFAS_CLIENT_ID = "DB-PROD"
HAFAS_CLIENT_TYPE = "WEB"
HAFAS_CLIENT_NAME = "HAFAS"
HAFAS_CLIENT_LABEL = "Zuginfo.nrw"
HAFAS_CLIENT_VERSION = "1111"
HAFAS_EXT = "DB.R21.12.a"

# Liste aller auswählbaren Linien in NRW
NRW_LINES = [
    "RE 1", "RE 2", "RE 3", "RE 4", "RE 5", "RE 6", "RE 7", "RE 8", "RE 9",
    "RE 10", "RE 11", "RE 13", "RE 14", "RE 16", "RE 17", "RE 18", "RE 19",
    "RE 42", "RE 44", "RE 49", "RE 57",
    "RB 20", "RB 27", "RB 32", "RB 33", "RB 34", "RB 35", "RB 39", "RB 40",
    "RB 48", "RB 50", "RB 52", "RB 59", "RB 61", "RB 65", "RB 66", "RB 67",
    "RB 69", "RB 71", "RB 72", "RB 73", "RB 89", "RB 91",
    "S 1", "S 2", "S 3", "S 4", "S 5", "S 6", "S 7", "S 8", "S 9",
    "S 11", "S 12", "S 19", "S 23", "S 28", "S 68",
]

# Ausblendbare Kategorien im Optionen-Menü
CATEGORY_EXCLUDE_OPTIONS = {
    "elevator": "Aufzugsstörungen (Aufzug außer Betrieb)",
    "construction": "Allgemeine Bauarbeiten / Vorankündigungen",
}
