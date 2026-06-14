from __future__ import annotations

import aiohttp
import logging
import random
import string
import re
from html import unescape

BASE_URL = "https://zuginfo.nrw/him/HimSearch"
PRE_URL = "https://www.zuginfo.nrw/app/"

_LOGGER = logging.getLogger(__name__)
# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------

def _random_request_id(length=8):
    """Erzeugt eine zufällige Request-ID wie ein Browser."""
    import random
    import string
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _html_to_markdown(html: str) -> str:
    """Konvertiert HTML aus HIM-Meldungen in reinen Text."""
    if not html:
        return ""
    from html import unescape
    import re

    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()
# ---------------------------------------------------------
# Datenmodell: NRWMessage
# ---------------------------------------------------------

class NRWMessage:
    """Repräsentiert eine einzelne HIM-Meldung aus Zuginfo.nrw."""

    def __init__(self, raw, common):
        self.raw = raw
        self.common = common

        # Basisdaten
        self.id = raw.get("hid")
        self.title = raw.get("head")
        self.text_html = raw.get("text")
        self.text = _html_to_markdown(self.text_html)

        # Status / Metadaten
        self.active = raw.get("act", False)
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

    # -----------------------------------------------------
    # Auflösung von Referenzen
    # -----------------------------------------------------

    def _resolve_locations(self):
        locL = self.common.get("locL", [])
        result = []

        for edge in self._resolve_edges():
            for loc_idx in [edge.get("from"), edge.get("to")]:
                if loc_idx is not None and 0 <= loc_idx < len(locL):
                    loc = locL[loc_idx]
                    result.append({
                        "name": loc.get("name"),
                        "id": loc.get("extId"),
                        "type": loc.get("type"),
                        "lat": loc.get("crd", {}).get("y"),
                        "lon": loc.get("crd", {}).get("x"),
                    })

        return result

    def _resolve_products(self):
        prodL = self.common.get("prodL", [])
        result = []

        for idx in self.prod_refs:
            if 0 <= idx < len(prodL):
                prod = prodL[idx]
                result.append({
                    "name": prod.get("name"),
                    "line": prod.get("line"),
                    "number": prod.get("number"),
                    "operator": prod.get("oprX"),
                })

        return result

    def _resolve_edges(self):
        edges = self.common.get("himMsgEdgeL", [])
        result = []

        for idx in self.edge_refs:
            if 0 <= idx < len(edges):
                edge = edges[idx]
                result.append({
                    "from": edge.get("fLocX"),
                    "to": edge.get("tLocX"),
                    "dir": edge.get("dir"),
                })

        return result

    def _resolve_events(self):
        events = self.common.get("himMsgEventL", [])
        result = []

        for idx in self.event_refs:
            if 0 <= idx < len(events):
                ev = events[idx]
                result.append({
                    "type": ev.get("type"),
                    "text": ev.get("txt"),
                    "time": ev.get("t"),
                })

        return result
# ---------------------------------------------------------
# API-Client: NRWHimApi (Teil 1)
# ---------------------------------------------------------

class NRWHimApi:
    """Client für die HAFAS-HIM-API von Zuginfo.nrw."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def _prepare_session(self):
        """Lädt die Web-App wie ein Browser, um Session-Cookies zu erhalten."""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.6367.91 Safari/537.36",

            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,image/apng,*/*;q=0.8",

            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",

            # Chrome Client Hints
            "Sec-CH-UA": "\"Chromium\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": "\"Windows\"",
            "Sec-CH-UA-Platform-Version": "\"15.0.0\"",
            "Sec-CH-UA-Arch": "\"x86\"",
            "Sec-CH-UA-Bitness": "\"64\"",
            "Sec-CH-UA-Full-Version": "\"124.0.6367.91\"",
            "Sec-CH-UA-Full-Version-List":
                "\"Chromium\";v=\"124.0.6367.91\", \"Not-A.Brand\";v=\"99.0.0.0\"",

            # Chrome Navigation
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.zuginfo.nrw/",
        }

        async with self.session.get(PRE_URL, headers=headers) as resp:
            _LOGGER.debug("PRE_URL status: %s", resp.status)
    async def fetch_messages(self):
        """Holt HIM-Meldungen von Zuginfo.nrw."""

        # Schritt 1: PRE-Request (Cookies holen)
        await self._prepare_session()

        # Schritt 2: Request-Payload wie im Browser
        payload = {
            "req": {
                "ver": "1.24",
                "lang": "de",
                "auth": {"type": "AID", "aid": "hafas-nrw-app"},
                "client": {"id": "NRW", "type": "WEB", "name": "webapp"},
                "svcReqL": [{
                    "req": {
                        "himFltrL": [{"type": "PROD", "mode": "INC", "value": "0"}],
                        "getEdges": True,
                        "getEvents": True,
                        "getProds": True,
                        "getCats": True,
                    },
                    "meth": "HimSearch"
                }],
            },
            "id": _random_request_id(),
        }

        # Cookie-Debug
        _LOGGER.error("Cookies after PRE_URL: %s",
                      self.session.cookie_jar.filter_cookies(PRE_URL))

    # Schritt 3: POST-Request an die HIM-API
        # Schritt 3: POST-Request an die HIM-API
        async with self.session.post(
            BASE_URL,
            json=payload,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0.6367.91 Safari/537.36",

                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br, zstd",

                "Sec-CH-UA": "\"Chromium\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": "\"Windows\"",
                "Sec-CH-UA-Platform-Version": "\"15.0.0\"",
                "Sec-CH-UA-Arch": "\"x86\"",
                "Sec-CH-UA-Bitness": "\"64\"",
                "Sec-CH-UA-Full-Version": "\"124.0.6367.91\"",
                "Sec-CH-UA-Full-Version-List":
                    "\"Chromium\";v=\"124.0.6367.91\", \"Not-A.Brand\";v=\"99.0.0.0\"",

                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",

                "Origin": "https://www.zuginfo.nrw",
                "Referer": "https://www.zuginfo.nrw/",
                "Connection": "keep-alive",
                "Priority": "u=1, i",

                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        ) as resp:
            raw_text = await resp.text()

            _LOGGER.debug("RAW POST RESPONSE: %s", raw_text)
        # Schritt 3b: Cookie-Debug nach POST
       raw_text = await resp.text()
        _LOGGER.debug("RAW POST RESPONSE: %s", raw_text)

        # Schritt 3b: Cookie-Debug nach POST
        _LOGGER.error("Cookies after POST: %s",
                      self.session.cookie_jar.filter_cookies(BASE_URL))

        # Wenn der Server HTML statt JSON liefert → Hinweis ausgeben
        if "html" in resp.headers.get("Content-Type", "").lower():
            _LOGGER.error("Server lieferte HTML statt JSON. Vermutlich fehlende Session.")
            _LOGGER.error("Erste 500 Zeichen HTML: %s", raw_text[:500])
            return []
 
        # Schritt 4: JSON-Antwort parsen
        try:
            data = await resp.json(content_type=None)
        except Exception as e:
            _LOGGER.error("Konnte JSON nicht parsen: %s", e)
            _LOGGER.error("Antwort war: %s", raw_text)
            return []

        # Schritt 5: Struktur prüfen
        try:
            svc = data["svcResL"][0]["res"]
        except Exception as e:
            _LOGGER.error("Unerwartete JSON-Struktur: %s", e)
            _LOGGER.error("Antwort war: %s", raw_text)
            return []

        msgL = svc.get("msgL", [])
        common = svc.get("common", {})

        # Schritt 6: NRWMessage-Objekte erzeugen
        messages = []
        for msg in msgL:
            try:
                messages.append(NRWMessage(msg, common))
            except Exception as e:
                _LOGGER.error("Fehler beim Erstellen einer NRWMessage: %s", e)

        return messages

    async with self.session.post(
        BASE_URL,
        json=payload,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.6367.91 Safari/537.36",

            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",

            "Sec-CH-UA": "\"Chromium\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": "\"Windows\"",
            "Sec-CH-UA-Platform-Version": "\"15.0.0\"",
            "Sec-CH-UA-Arch": "\"x86\"",
            "Sec-CH-UA-Bitness": "\"64\"",
            "Sec-CH-UA-Full-Version": "\"124.0.6367.91\"",
            "Sec-CH-UA-Full-Version-List":
                "\"Chromium\";v=\"124.0.6367.91\", \"Not-A.Brand\";v=\"99.0.0.0\"",

            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",

            "Origin": "https://www.zuginfo.nrw",
            "Referer": "https://www.zuginfo.nrw/",
            "Connection": "keep-alive",
            "Priority": "u=1, i",

            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
    ) as resp:
        raw_text = await resp.text()
        _LOGGER.debug("RAW POST RESPONSE: %s", raw_text)
