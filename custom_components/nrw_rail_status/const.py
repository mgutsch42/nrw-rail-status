"""Constants for the NRW Rail Status integration."""

DOMAIN = "nrw_rail_status"

# Update interval in seconds
DEFAULT_UPDATE_INTERVAL = 60

# Sensor name
SENSOR_NAME = "NRW Rail Status"

# -----------------------------
# HAFAS / Zuginfo API constants
# -----------------------------

# Base URL for the Zuginfo NRW gateway
BASE_URL = "https://zuginfo.nrw/gate/"

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
