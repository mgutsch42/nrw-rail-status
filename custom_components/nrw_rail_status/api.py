"""API client for NRW Rail Status / Zuginfo.nrw."""

from __future__ import annotations

import logging
import random
import re
import string
from datetime import datetime
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
)

_LOGGER = logging.getLogger(__name__)


class NRWHimApiError(Exception):
    """Fehler bei der Abfrage der Zuginfo.nrw-Schnittstelle."""


def _random_request_id(length: int = 8) -> str:
    """Erzeugt eine zufaellige Anfrage-ID wie ein Browser."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _html_to_text(html: str) -> str:
    """Wandelt HTML aus den Meldungen in reinen Text um."""
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class NRWMessage:
    """Repraesentiert eine einzelne HIM-Meldung aus Zuginfo.nrw."""

    def __init__(self, raw: dict, common: dict) -> None:
        """Meldung anlegen."""
        self.raw = raw
        self.common = common

        self.id = raw.get("hid") or raw.get("id")
        self.title = raw.get("head") or raw.get("title")
        self.text_html = raw.get("text") or raw.get("desc")
        self.text = _html_to_text(self.text_html)

        self.active = raw.get("act", True)
        self.priority = raw.get("prio")
        self.product = raw.get("prod")
        self.comp = raw.get("comp")

        self.start_date = raw.get("sDate")
        self.start_time = raw.get("sTime")
        self.end_date = raw.get("eDate")
        self.end_time = raw.get("eTime")

        self.category_refs = raw.get("catRefL", [])
        self.edge_refs = raw.get("edgeRefL", [])
        self.event_refs = raw.get("eventRefL", [])
        self.prod_refs = raw.get("affProdRefL", [])

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
    """Client fuer die HAFAS-HIM-Schnittstelle von Zuginfo.nrw."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Client anlegen."""
        self.session = session

    async def fetch_messages(self) -> list[NRWMessage]:
        """Holt HIM-Meldungen von Zuginfo.nrw."""
        request_id = _random_request_id()

        heute = datetime.now().strftime("%Y%m%d")

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
                        "dateB": heute,
                        "timeB": "000000",
                        "dateE": heute,
                        "timeE": "235959",
                        "getParent": True,
                        "getChildren": True,
                    },
                    "id": "1|1|",
                }
            ],
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9",
            "Content-Type": "application/json",
            "Origin": "[vrr.hafas.cloud](https://vrr.hafas.cloud)",
            "Referer": "[vrr.hafas.cloud](https://vrr.hafas.cloud/)",
        }

        _LOGGER.debug("Sende HimSearch-Anfrage an %s", BASE_URL)

        try:
            async with self.session.post(
                BASE_URL, json=payload, headers=headers
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise NRWHimApiError(
                        f"HAFAS antwortete mit Status {resp.status}: {body[:300]}"
                    )
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise NRWHimApiError(f"Verbindungsfehler: {err}") from err

        # Fehler, die die Bahn IM Datenpaket meldet (nicht als HTTP-Status).
        entry = (data.get("svcResL") or [{}])[0]
        err_code = entry.get("err")
        if err_code and err_code != "OK":
            raise NRWHimApiError(
                f"HAFAS meldete Fehler '{err_code}': "
                f"{entry.get('errTxt', 'ohne Beschreibung')}"
            )

        svc = entry.get("res")
        if not isinstance(svc, dict):
            raise NRWHimApiError("HAFAS-Antwort enthielt keine Daten.")

        common = svc.get("common", {})
        msgL = svc.get("msgL") or svc.get("msgList") or svc.get("himL") or []

        if not isinstance(msgL, list):
            raise NRWHimApiError("Meldungsliste hatte ein unerwartetes Format.")

        messages: list[NRWMessage] = []
        for msg in msgL:
            try:
                messages.append(NRWMessage(msg, common))
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Eine Meldung konnte nicht gelesen werden: %s", err)

        _LOGGER.info("%s HIM-Meldungen geladen.", len(messages))

        # Zeigt im Log, wie die Linien wirklich geschrieben werden.
        for m in messages[:10]:
            for p in m.products:
                _LOGGER.debug(
                    "Linie in der Meldung: name=%r line=%r",
                    p.get("name"),
                    p.get("line"),
                )

        return messages
