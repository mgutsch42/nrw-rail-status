"""API client for NRW Rail Status / Zuginfo.nrw."""

from __future__ import annotations

import logging
import random
import re
import string
from datetime import datetime, timedelta
from html import unescape

import aiohttp

from .const import (
    BASE_URL,
    HAFAS_AID,
    HAFAS_CLIENT_ID,
    HAFAS_CLIENT_LABEL,
    HAFAS_CLIENT_NAME,
    HAFAS_CLIENT_TYPE,
    HAFAS_CLIENT_VERSION,
    HAFAS_EXT,
    HAFAS_LANG,
    HAFAS_VERSION,
    MAIN_URL,
)

_LOGGER = logging.getLogger(__name__)


def _random_request_id(length: int = 8) -> str:
    """Erzeugt eine zufällige Request-ID wie ein Browser."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _html_to_markdown(html: str) -> str:
    """Konvertiert HTML aus HIM-Meldungen in reinen Text."""
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class NRWMessage:
    """Repräsentiert eine einzelne HIM-Meldung aus Zuginfo.nrw."""

    def __init__(self, raw: dict, common: dict) -> None:
        """Initialize the message object."""
        self.raw = raw
        self.common = common

        # Basisdaten
        self.id = raw.get("hid")
        self.title = raw.get("head")
        self.text_html = raw.get("text")
        self.text = _html_to_markdown(self.text_html)

        # Status / Metadaten
        self.active = raw.get("act", True)
        self.priority = raw.get("prio")
        self.product = raw.get("prod")
        self.comp = raw.get("comp")

        # Zeitliche Angaben
        self.start_date = raw.get("sDate")
        self.start_time = raw.get("sTime")
        self.end_date = raw.get("eDate")
        self.end_time = raw.get("eTime")

        # Referenzen
        self.category_refs = raw.get("catRefL", [])
        self.edge_refs = raw.get("edgeRefL", [])
        self.event_refs = raw.get("eventRefL", [])
        self.prod_refs = raw.get("affProdRefL", [])

        # Aufgelöste Daten
        self.locations = self._resolve_locations()
        self.products = self._resolve_products()
        self.edges = self._resolve_edges()
        self.events = self._resolve_events()

    def _resolve_locations(self) -> list[dict]:
        locL = self.common.get("locL", [])
        result = []

        for edge in self._resolve_edges():
            for loc_idx in [edge.get("from"), edge.get("to")]:
                if loc_idx is not None and 0 <= loc_idx < len(locL):
                    loc = locL[loc_idx]
                    result.append(
                        {
                            "name": loc.get("name"),
                            "id": loc.get("extId"),
                            "type": loc.get("type"),
                            "lat": loc.get("crd", {}).get("y"),
                            "lon": loc.get("crd", {}).get("x"),
                        }
                    )
        return result

    def _resolve_products(self) -> list[dict]:
        prodL = self.common.get("prodL", [])
        result = []

        for idx in self.prod_refs:
            if 0 <= idx < len(prodL):
                prod = prodL[idx]
                result.append(
                    {
                        "name": prod.get("name"),
                        "line": prod.get("line"),
                        "number": prod.get("number"),
                        "operator": prod.get("oprX"),
                    }
                )
        return result

    def _resolve_edges(self) -> list[dict]:
        edges = self.common.get("himMsgEdgeL", [])
        result = []

        for idx in self.edge_refs:
            if 0 <= idx < len(edges):
                edge = edges[idx]
                result.append(
                    {
                        "from": edge.get("fLocX"),
                        "to": edge.get("tLocX"),
                        "dir": edge.get("dir"),
                    }
                )
        return result

    def _resolve_events(self) -> list[dict]:
        events = self.common.get("himMsgEventL", [])
        result = []

        for idx in self.event_refs:
            if 0 <= idx < len(events):
                ev = events[idx]
                result.append(
                    {
                        "type": ev.get("type"),
                        "text": ev.get("txt"),
                        "time": ev.get("t"),
                    }
                )
        return result


class NRWHimApi:
    """Client für die HAFAS-HIM-API von Zuginfo.nrw."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self.session = session

    async def _prepare_session(self) -> None:
        """Lädt die Hauptseite, um Session-Cookies zu erhalten."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9",
        }

        try:
            async with self.session.get(MAIN_URL, headers=headers) as resp:
                _LOGGER.debug("Hauptseite Status: %s", resp.status)
        except Exception as err:
            _LOGGER.warning("Fehler beim Vorbereiten der Session über Hauptseite: %s", err)

    async def fetch_messages(self) -> list[NRWMessage]:
        """Holt HIM-Meldungen von Zuginfo.nrw."""
        await self._prepare_session()

        request_id = _random_request_id()

        now = datetime.now()
        date_begin = (now - timedelta(days=2)).strftime("%Y%m%d")
        date_end = (now + timedelta(days=180)).strftime("%Y%m%d")

        payload = {
            "id": request_id,
            "ver": HAFAS_VERSION,
            "lang": HAFAS_LANG,
            "auth": {
                "type": "AID",
                "aid": HAFAS_AID,
            },
            "client": {
                "id": HAFAS_CLIENT_ID,
                "type": HAFAS_CLIENT_TYPE,
                "name": HAFAS_CLIENT_NAME,
                "l": HAFAS_CLIENT_LABEL,
                "v": HAFAS_CLIENT_VERSION,
            },
            "formatted": False,
            "ext": HAFAS_EXT,
            "svcReqL": [
                {
                    "meth": "HimSearch",
                    "req": {
                        "maxNum": 500,
                        "dateB": date_begin,
                        "timeB": "000000",
                        "dateE": date_end,
                        "timeE": "235959",
                        "getParent": True,
                        "getChildren": True,
                    },
                    "id": "1|1|",
                }
            ],
        }

        rnd = random.randint(10**12, 10**13 - 1)
        url = (
            f"{BASE_URL}"
            f"?requestId={request_id}"
            f"&hciMethod=HimSearch"
            f"&hciVersion={HAFAS_VERSION}"
            f"&hciClientType={HAFAS_CLIENT_TYPE}"
            f"&hciClientVersion={HAFAS_CLIENT_VERSION}"
            f"&aid={HAFAS_AID}"
            f"&rnd={rnd}"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://www.zuginfo.nrw",
            "Referer": "https://www.zuginfo.nrw/",
        }

        _LOGGER.debug("Sende POST-Request an %s", url)

        async with self.session.post(url, json=payload, headers=headers) as resp:
            _LOGGER.debug("API Response HTTP Status: %s", resp.status)

            if resp.status != 200:
                _LOGGER.error("Zuginfo API lieferte HTTP Status %s", resp.status)
                return []

            try:
                data = await resp.json(content_type=None)
            except Exception as e:
                raw_body = await resp.text()
                _LOGGER.error("Konnte JSON nicht parsen: %s. Body: %s", e, raw_body[:200])
                return []

            _LOGGER.debug("API Antwort erhalten: %s", str(data)[:300])

            try:
                svc = data["svcResL"][0]["res"]
            except (KeyError, IndexError, TypeError) as e:
                _LOGGER.error("Unerwartete JSON-Struktur der API: %s | Inhalt: %s", e, data)
                return []

            common = svc.get("common", {})
            msgL = svc.get("himL", [])

            if not isinstance(msgL, list):
                _LOGGER.warning("'himL' ist keine Liste oder leer.")
                return []

            _LOGGER.info("Erfolgreich %s HIM-Meldungen von Zuginfo.nrw geladen.", len(msgL))

            messages = []
            for msg in msgL:
                try:
                    messages.append(NRWMessage(msg, common))
                except Exception as e:
                    _LOGGER.error("Fehler beim Erstellen der NRWMessage: %s", e)

            return messages
