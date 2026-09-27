"""Constants for the NRW Rail Status integration."""

from typing import Final

DOMAIN: Final = "nrw_rail_status"

# API Endpunkte
BASE_URL: Final = "https://www.zuginfo.nrw/gate/"
MAIN_URL: Final = "https://www.zuginfo.nrw/webapp/"

# HAFAS API Parameter
HAFAS_VERSION: Final = "1.24"
HAFAS_LANG: Final = "deu"
HAFAS_AID: Final = "23lkjh63l456oisplergn"
HAFAS_CLIENT_ID: Final = "HAFAS"
HAFAS_CLIENT_TYPE: Final = "WEB"
HAFAS_CLIENT_NAME: Final = "webapp"
HAFAS_CLIENT_LABEL: Final = "vs_webapp"
HAFAS_CLIENT_VERSION: Final = 10107
HAFAS_EXT: Final = "VRR.1"
