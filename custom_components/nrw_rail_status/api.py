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
)

_LOGGER = logging.getLogger(__name__)


def _random_request_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _html_to_markdown(html: str) -> str:
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


class NRWMessage:
    """Repräsentiert eine einzelne HIM-Meldung aus Zuginfo.nrw."""

    def __init__(self, raw: dict, common: dict) -> None:
        self.raw = raw
        self.common = common

        self.id = raw.get("hid") or raw.get("id")
        self.title = raw.get("head") or raw.get("title")
        self.text_html = raw.get("text") or raw.get("desc")
        self.text = _html_to_markdown(self.text_html)

        self.active = raw.get("act", True)
        self.priority = raw.get("prio")
        self.product = raw.get("prod")

        self.prod_refs = raw.get("affProdRefL", [])
        self.products = self._resolve_products()

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
                    }
                )
        return result


class NRWHimApi:
    """Client für die HAFAS-HIM-API von Zuginfo.nrw."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def fetch_messages(self) -> list[NRWMessage]:
        request_id = _random_request_id()
        now = datetime.now()
        date_begin = (now - timedelta(days=2)).strftime("%Y%m%d")
        date_end = (now + timedelta(days=180)).strftime("%Y%m%d")

        payload = {
            "id": request_id,
            "ver": HAFAS_VERSION,
            "lang": HAFAS_LANG,
            "auth": {"type": "AID", "aid": HAFAS_AID},
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

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }

        async with self.session.post(BASE_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                _LOGGER.error("Zuginfo API HTTP-Fehler %s", resp.status)
                return []

            try:
                data = await resp.json(content_type=None)
                svc = data["svcResL"][0]["res"]
                common = svc.get("common", {})
                msgL = svc.get("msgL") or svc.get("msgList") or svc.get("himL") or []
            except Exception as e:
                _LOGGER.error("Fehler beim Verarbeiten der Antwort: %s", e)
                return []

            messages = []
            for msg in msgL:
                try:
                    messages.append(NRWMessage(msg, common))
                except Exception as e:
                    _LOGGER.error("Fehler beim Erstellen der NRWMessage: %s", e)

            return messages
