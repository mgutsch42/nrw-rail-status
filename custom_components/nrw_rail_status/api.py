"""API client for NRW Rail Status / Zuginfo.nrw.

Zwei Wege zu denselben Meldungen:

1. **HTML-Weg** (Standard, funktioniert ohne Session)
   Die oeffentliche Seite https://www.zuginfo.nrw/ liefert die Meldungen
   serverseitig gerendert aus. Gefiltert wird ueber URL-Parameter:

       ?categories=0,4,2,3,1&sParam=LMOD_&sIncrease=DESC&lineLbl=RE 13,RB 91

   Diese Quelle ist stabil erreichbar und enthaelt alle Felder, die auf dem
   Dashboard gebraucht werden: Titel, Kategorie, Veroeffentlichungszeit,
   Zeitraum (Beginn/Ende), betroffene Linien und den Meldungstext.

2. **HAFAS-Weg** (Rueckfall, sofern erreichbar)
   Der bestehende HAFAS-HIM-Client gegen vrr.hafas.cloud. Dieser Endpunkt
   verlangt eine endpunkt-spezifische Pruefsumme (checkV); ohne sie antwortet
   er mit einem Fehler im Datenpaket. Der Weg bleibt deshalb erhalten, wird
   aber nur benutzt, wenn der HTML-Weg nichts liefert.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import string
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import quote as url_quote

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

# Die oeffentliche Meldungsseite. Ueber die Parameter laesst sie sich nach
# Linien und Kategorien filtern, genau wie es die Webseite selbst tut.
WEB_URL = "https://www.zuginfo.nrw/"

# Kategorien der Seite. Die Reihenfolge ist die Auswahlliste der Webseite.
CATEGORIES_ALL = "0,4,2,3,1"

# Kategorie-Namen, wie sie auf der Seite stehen.
CATEGORY_BY_LABEL = {
    "information": "Information",
    "bauarbeiten": "Bauarbeiten",
    "stoerung": "Störung",
    "störung": "Störung",
    "grossstoerung": "Großstörung",
    "großstörung": "Großstörung",
    "beeintraechtigung": "Beeinträchtigung",
    "beeinträchtigung": "Beeinträchtigung",
}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


class NRWHimApiError(Exception):
    """Fehler bei der Abfrage der Zuginfo.nrw-Schnittstelle."""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _random_request_id(length: int = 8) -> str:
    """Erzeugt eine zufaellige Anfrage-ID wie ein Browser."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _html_to_text(html: str) -> str:
    """Wandelt HTML in reinen Text um."""
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_MONTHS = {
    "januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
}


def _parse_german_date(value: str) -> str | None:
    """Wandelt '24.10.2026, 14:43' in ISO um. Gibt None zurueck, wenn unklar."""
    if not value:
        return None
    # Form 1: 24.10.2026, 14:43
    m = re.search(
        r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})(?:,\s*(\d{1,2}):(\d{2}))?",
        value,
    )
    if m:
        day, month, year, hour, minute = m.groups()
    else:
        # Form 2: 24. Oktober 2026, 14:43
        m2 = re.search(
            r"(\d{1,2})\.\s*([A-Za-zÄÖÜäöüß]+)\s*(\d{4})"
            r"(?:,\s*(\d{1,2}):(\d{2}))?",
            value,
        )
        if not m2:
            return None
        day, mon_name, year, hour, minute = m2.groups()
        month = _MONTHS.get(mon_name.strip().lower())
        if month is None:
            return None

    try:
        dt = datetime(
            int(year), int(month), int(day),
            int(hour) if hour else 0, int(minute) if minute else 0,
        )
    except ValueError:
        return None
    return dt.isoformat()


def _clean_line_label(label: str) -> str:
    """Normalisiert ein Linienkuerzel: 'RE 13' bleibt 'RE 13'."""
    return re.sub(r"\s+", " ", (label or "").strip())


def _normalize_for_compare(label: str) -> str:
    """Vergleichsform eines Linienkuerzels: 'RE 13' -> 'RE13'."""
    return re.sub(r"[\s\-]", "", (label or "").upper())


# ---------------------------------------------------------------------------
# Meldungsobjekt
# ---------------------------------------------------------------------------

class NRWMessage:
    """Eine einzelne Meldung aus Zuginfo.nrw.

    Traegt beide Quellen: die HAFAS-Felder (falls dieser Weg benutzt wurde)
    und die Felder der Webseite. Nach aussen ist die Struktur dieselbe.
    """

    def __init__(self, raw: dict | None = None, common: dict | None = None) -> None:
        """Meldung anlegen."""
        self.raw = raw or {}
        self.common = common or {}

        # --- HAFAS-Form --------------------------------------------------
        r = self.raw
        self.id = r.get("hid") or r.get("id")
        self.title = r.get("head") or r.get("title") or ""
        self.text_html = r.get("text") or r.get("desc")
        self.text = _html_to_text(self.text_html or "")

        self.active = r.get("act", True)
        self.priority = r.get("prio")
        self.product = r.get("prod")
        self.comp = r.get("comp")

        self.start_date = r.get("sDate")
        self.start_time = r.get("sTime")
        self.end_date = r.get("eDate")
        self.end_time = r.get("eTime")

        self.category_refs = r.get("catRefL", [])
        self.edge_refs = r.get("edgeRefL", [])
        self.event_refs = r.get("eventRefL", [])
        self.prod_refs = r.get("affProdRefL", [])

        # --- Felder der Webseite (werden vom HTML-Parser gefuellt) -------
        self.category: str | None = None
        self.published_at: str | None = None
        self.period_start: str | None = None
        self.period_end: str | None = None
        self.url: str | None = None
        self.source: str = "hafas" if raw else "web"
        self.line_labels: list[str] = []

        self.locations = self._resolve_locations()
        self.products = self._resolve_products()
        self.edges = self._resolve_edges()
        self.events = self._resolve_events()

    # --- HAFAS-Referenzen ------------------------------------------------

    def _resolve_locations(self) -> list[dict]:
        locL = self.common.get("locL", [])
        result = []
        for edge in self._resolve_edges():
            for loc_idx in (edge.get("from"), edge.get("to")):
                if loc_idx is not None and 0 <= loc_idx < len(locL):
                    loc = locL[loc_idx]
                    result.append({
                        "name": loc.get("name"),
                        "id": loc.get("extId"),
                        "type": loc.get("type"),
                        "lat": (loc.get("crd") or {}).get("y"),
                        "lon": (loc.get("crd") or {}).get("x"),
                    })
        return result

    def _resolve_products(self) -> list[dict]:
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

    def _resolve_edges(self) -> list[dict]:
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

    def _resolve_events(self) -> list[dict]:
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

    # --- einheitliche Sicht nach aussen ----------------------------------

    @property
    def line_names(self) -> list[str]:
        """Alle Linienkuerzel dieser Meldung, egal aus welcher Quelle."""
        if self.line_labels:
            return self.line_labels
        names = []
        for p in self.products:
            if p.get("name"):
                names.append(_clean_line_label(str(p["name"])))
        return names

    @property
    def period(self) -> str:
        """Lesbarer Zeitraum, z. B. '17.10.2026 06:00 - 31.10.2026 22:00'."""
        if not self.period_start and not self.period_end:
            return ""
        start = self.period_start or "?"
        end = self.period_end or "offen"
        return f"{start} - {end}"

    def as_dict(self) -> dict[str, Any]:
        """Flache Form fuer Sensor-Attribute."""
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "category": self.category,
            "lines": self.line_names,
            "published": self.published_at,
            "period": self.period,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "url": self.url,
            "source": self.source,
        }

    def matches_line(self, line: str) -> bool:
        """Prueft, ob diese Meldung die angegebene Linie betrifft."""
        want = _normalize_for_compare(line)
        if not want:
            return False
        for name in self.line_names:
            have = _normalize_for_compare(name)
            if not have:
                continue
            if want == have:
                return True
            # 'SEV RB 39' soll auch bei 'RB 39' treffen
            if want in have or have in want:
                return True
        return False


# ---------------------------------------------------------------------------
# HTML-Parser fuer die oeffentliche Meldungsseite
# ---------------------------------------------------------------------------

class ZuginfoWebParser:
    """Zerlegt die gerenderte Meldungsseite in NRWMessage-Objekte.

    Die Seite ist serverseitig gerendert; jede Meldung steht als
    <article class="card"> mit festen Bausteinen. Der Parser arbeitet mit
    regulaeren Ausdruecken, damit er keine zusaetzliche Abhaengigkeit braucht.
    """

    # Eine Meldung beginnt mit der Karte und endet vor der naechsten.
    _CARD_RE = re.compile(
        r"<article[^>]*class=\"[^\"]*\bcard\b[^\"]*\"[^>]*>(.*?)</article>",
        re.S | re.I,
    )

    # Fallback, falls die Seite ohne <article> rendert.
    _BLOCK_RE = re.compile(
        r"(<h3[^>]*>.*?</h3>.*?)(?=<h3[^>]*>|\Z)", re.S | re.I
    )

    _H_RE = re.compile(r"<h[234][^>]*>(.*?)</h[234]>", re.S | re.I)
    _DATE_RE = re.compile(
        r"(\d{1,2}\.\s*(?:\d{1,2}|"
        r"Januar|Februar|M(?:ä|ae)rz|April|Mai|Juni|Juli|August|September|"
        r"Oktober|November|Dezember)"
        r"\.?\s*\d{4}(?:,\s*\d{1,2}:\d{2})?)",
        re.I,
    )
    _PERIOD_RE = re.compile(
        r"(?:Beginn|Von)\s*:?\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}[^<\n]{0,20}?)"
        r"\s*(?:Ende|Bis)\s*:?\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}[^<\n]{0,20})",
        re.S | re.I,
    )
    _MSG_LINK_RE = re.compile(r"zuginfo\.nrw/\?msg=(\d+)", re.I)
    # Linienkuerzel stehen als <strong>RE 13</strong> oder **RE 13**
    _LINE_RE = re.compile(
        r"\b((?:RE|RB|S|SEV)\s?\d{1,3}(?:\s?\(RRX\))?(?:\s?(?:Nord|Süd|RLP))?)\b"
    )
    _CAT_RE = re.compile(
        r"(Bauarbeiten|Störung|Stoerung|Großstörung|Grossstoerung|"
        r"Beeinträchtigung|Beeintraechtigung|Information)",
        re.I,
    )

    def parse(self, html: str) -> list[NRWMessage]:
        """Liefert die Meldungen der Seite."""
        if not html:
            return []

        blocks = self._CARD_RE.findall(html)
        if not blocks:
            _LOGGER.debug("Keine <article class=card> gefunden, nutze Fallback.")
            blocks = [m.group(1) for m in self._BLOCK_RE.finditer(html)]

        messages: list[NRWMessage] = []
        for block in blocks:
            msg = self._parse_block(block)
            if msg and msg.title:
                messages.append(msg)

        # Doppelte Meldungen ueber die ID entfernen
        unique: dict[str, NRWMessage] = {}
        for m in messages:
            key = str(m.id or m.title)
            if key not in unique:
                unique[key] = m
        return list(unique.values())

    # --- eine einzelne Karte --------------------------------------------

    def _parse_block(self, block: str) -> NRWMessage | None:
        msg = NRWMessage()

        # Titel steht in der ersten Ueberschrift der Karte
        h = self._H_RE.search(block)
        if not h:
            return None
        msg.title = _html_to_text(h.group(1))
        if not msg.title:
            return None

        # Link zur Einzelmeldung
        link = self._MSG_LINK_RE.search(block)
        if link:
            msg.id = link.group(1)
            msg.url = f"https://www.zuginfo.nrw/?msg={link.group(1)}"

        # Kategorie, sofern ausgeschrieben
        cat = self._CAT_RE.search(_html_to_text(block))
        if cat:
            key = cat.group(1).lower()
            msg.category = CATEGORY_BY_LABEL.get(key, cat.group(1))

        # Aufbau der Karte auf der Seite:
        #   <Kopf mit Linien und Datum>  <h3>Titel</h3>  <Zeitraum>  <Text>
        #
        # Gesucht wird also: Zeitraum zuerst, Veroeffentlichungsdatum im Kopf
        # VOR der Ueberschrift. Damit sind beide Felder unabhaengig davon, in
        # welcher Reihenfolge die Seite sie ausgibt.
        kopf_html = block[:h.start()] if h.start() > 0 else ""
        text_plain = _html_to_text(block)
        kopf_text = _html_to_text(kopf_html)

        # Zeitraum aus 'Beginn ... Ende ...'
        period = self._PERIOD_RE.search(text_plain)
        if period:
            msg.period_start = re.sub(r"\s+", " ", period.group(1)).strip()
            msg.period_end = re.sub(r"\s+", " ", period.group(2)).strip()

        # Veroeffentlichungszeit: im Kopf der Karte, also vor der Ueberschrift
        kopf_dates = self._DATE_RE.findall(kopf_text)
        if kopf_dates:
            msg.published_at = _parse_german_date(kopf_dates[-1])
        elif period and not msg.period_start:
            pass
        else:
            # Kein Kopfdatum vorhanden: notfalls das erste Datum nach dem Titel,
            # das nicht zum Zeitraum gehoert.
            after_title = text_plain[h.end():] if h.end() < len(text_plain) else ""
            after_title = self._PERIOD_RE.sub(" ", after_title)
            rest_dates = self._DATE_RE.findall(after_title)
            if rest_dates:
                msg.published_at = _parse_german_date(rest_dates[0])

        # Betroffene Linien
        seen: list[str] = []
        for hit in self._LINE_RE.finditer(_html_to_text(block)):
            label = _clean_line_label(hit.group(1))
            if label not in seen:
                seen.append(label)
        msg.line_labels = seen

        # Text: alles nach dem Zeitraum, ohne die Linienaufzaehlung
        text = text_plain
        text = re.sub(r"^.*?" + re.escape(msg.title), "", text, count=1, flags=re.S)
        text = re.sub(r"^(?:\s*(?:Beginn|Ende|Von|Bis)[^\n]*)+", "", text)
        msg.text = text.strip()[:1500]

        msg.source = "web"
        return msg


# ---------------------------------------------------------------------------
# HAFAS-Client
# ---------------------------------------------------------------------------

class NRWHimApi:
    """Client fuer Zuginfo.nrw.

    Benutzt standardmaessig die oeffentliche Meldungsseite. Der HAFAS-Weg
    bleibt als Rueckfall erhalten und kann ueber ``use_hafas=True`` erzwungen
    werden.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        lines: list[str] | None = None,
        excluded_categories: list[str] | None = None,
    ) -> None:
        """Client anlegen.

        ``excluded_categories`` enthaelt die Kategorie-Schluessel aus
        ``CATEGORY_EXCLUDE_OPTIONS``, die NICHT angezeigt werden sollen.
        """
        self.session = session
        self.lines = [_clean_line_label(x) for x in (lines or [])]
        self.excluded_categories = [str(c) for c in (excluded_categories or [])]
        self.categories = self._build_categories()
        self.parser = ZuginfoWebParser()
        self.last_error: str | None = None
        self.diagnostics: dict[str, Any] = {}

    def _build_categories(self) -> str:
        """Bildet die categories-Parameter aus den ausgeschlossenen Kategorien."""
        alle = [c.strip() for c in CATEGORIES_ALL.split(",") if c.strip()]
        rest = [c for c in alle if c not in self.excluded_categories]
        # Ohne Filter immer alle Kategorien anfragen.
        return ",".join(rest) if rest else CATEGORIES_ALL

    # --- oeffentlicher Einstieg ------------------------------------------

    async def fetch_messages(self, use_hafas: bool = False) -> list[NRWMessage]:
        """Holt Meldungen. Standardweg ist die oeffentliche Seite."""
        self.diagnostics = {
            "lines_filter": list(self.lines),
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }

        web_error: str | None = None
        messages: list[NRWMessage] = []

        if not use_hafas:
            try:
                messages = await self._fetch_web()
                self.diagnostics["web"] = {
                    "ok": True, "count": len(messages), "url": self._web_url(),
                }
            except Exception as err:  # noqa: BLE001
                web_error = f"{type(err).__name__}: {err}"
                self.diagnostics["web"] = {"ok": False, "error": web_error}
                _LOGGER.warning("Meldungsseite nicht lesbar: %s", web_error)
                # Vollstaendigen Stacktrace ins Log, damit sich Fehler in der
                # Seitenstruktur nachvollziehen lassen.
                _LOGGER.debug("Details zum Fehler:", exc_info=True)

            if messages:
                self.last_error = None
                return messages

        # Rueckfall (oder ausdruecklich gewuenscht): HAFAS versuchen
        try:
            messages = await self._fetch_hafas()
            self.diagnostics["hafas"] = {"ok": True, "count": len(messages)}
            self.last_error = None
            return messages
        except Exception as err:  # noqa: BLE001
            self.diagnostics["hafas"] = {"ok": False, "error": f"{type(err).__name__}: {err}"}
            _LOGGER.warning("HAFAS-Weg nicht nutzbar: %s", err)

        self.last_error = web_error or "Keine Meldungen von beiden Wegen erhalten."
        return []

    # --- Weg 1: oeffentliche Seite ---------------------------------------

    def _web_url(self) -> str:
        params = [
            f"categories={self.categories}",
            "sParam=LMOD_",
            "sIncrease=DESC",
        ]
        if self.lines:
            joined = ",".join(self.lines)
            params.append("lineLbl=" + url_quote(joined, safe=""))
        return WEB_URL + "?" + "&".join(params)

    async def _fetch_web(self) -> list[NRWMessage]:
        url = self._web_url()
        headers = {
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9",
        }
        async with self.session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise NRWHimApiError(
                    f"Meldungsseite antwortete mit Status {resp.status}: {body[:200]}"
                )
            html = await resp.text()

        messages = self.parser.parse(html)
        self.diagnostics["html_length"] = len(html)

        if self.diagnostics.get("debug_html"):
            self.diagnostics["html_snippet"] = html[:2000]

        _LOGGER.info("%s Meldungen von der Meldungsseite gelesen.", len(messages))
        return messages

    # --- Weg 2: HAFAS (unveraendert aus der Vorversion) -------------------

    async def _fetch_hafas(self) -> list[NRWMessage]:
        request_id = _random_request_id()
        rnd = random.randint(10**12, 10**13 - 1)
        heute = datetime.now().strftime("%Y%m%d")

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
            "svcReqL": [{
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
            }],
        }

        base = BASE_URL if BASE_URL.endswith("/") else f"{BASE_URL}/"
        url = (
            f"{base}?requestId={request_id}&hciMethod=HimSearch"
            f"&hciVersion={HAFAS_VERSION}&hciClientType={HAFAS_CLIENT_TYPE}"
            f"&hciClientVersion={HAFAS_CLIENT_VERSION}&aid={HAFAS_AID}&rnd={rnd}"
        )
        headers = {
            "User-Agent": _UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://vrr.hafas.cloud",
            "Referer": "https://vrr.hafas.cloud/",
        }

        async with self.session.post(
            url, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise NRWHimApiError(
                    f"HAFAS antwortete mit Status {resp.status}: {body[:200]}"
                )
            data = await resp.json(content_type=None)

        entry = (data.get("svcResL") or [{}])[0]
        err_code = entry.get("err")
        if err_code and err_code != "OK":
            raise NRWHimApiError(
                f"Schnittstelle meldete '{err_code}': "
                f"{entry.get('errTxt', 'ohne Beschreibung')}"
            )

        svc = entry.get("res")
        if not isinstance(svc, dict):
            raise NRWHimApiError("Die Antwort enthielt keine Daten.")

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
        return messages


# ---------------------------------------------------------------------------
# Diagnose: prueft beide Wege und beschreibt die gefundene Struktur
# ---------------------------------------------------------------------------

async def async_run_diagnostics(
    session: aiohttp.ClientSession, lines: list[str] | None = None
) -> dict[str, Any]:
    """Fuehrt beide Abfragen aus und beschreibt das Ergebnis.

    Gedacht fuer den Aufruf aus dem Home-Assistant-Dienst
    ``nrw_rail_status.diagnose``.
    """
    out: dict[str, Any] = {"ok": True}

    # Weg 1: oeffentliche Seite
    web = NRWHimApi(session, lines=lines)
    web.diagnostics["debug_html"] = True
    try:
        msgs = await web.fetch_messages()
        out["web"] = {
            "ok": True,
            "count": len(msgs),
            "lines_filter": web.lines,
            "sample": [m.as_dict() for m in msgs[:3]],
            "snippet": (web.diagnostics.get("html_snippet") or "")[:600],
        }
    except Exception as err:  # noqa: BLE001
        out["web"] = {"ok": False, "error": str(err)}

    # Weg 2: HAFAS
    hafas = NRWHimApi(session, lines=lines)
    try:
        msgs = await hafas.fetch_messages(use_hafas=True)
        out["hafas"] = {
            "ok": True,
            "count": len(msgs),
            "sample": [m.as_dict() for m in msgs[:3]],
        }
    except Exception as err:  # noqa: BLE001
        out["hafas"] = {"ok": False, "error": str(err)}

    return out
