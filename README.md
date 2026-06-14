# NRW Rail Status (Home Assistant Integration)

Diese Home‑Assistant‑Integration zeigt aktuelle Störungen, Baustellen und Meldungen aus dem nordrhein‑westfälischen Bahnnetz an.  
Die Daten stammen direkt aus Zuginfo.nrw und werden über die offizielle HAFAS‑HIM‑Schnittstelle abgerufen.

Die Integration ist vollständig lokal, benötigt keine Cloud‑Dienste und funktioniert ohne API‑Key.

---

## ✨ Features

- Echtzeit‑Abruf der NRW‑HIM‑Meldungen (Störungen, Baustellen, Ausfälle)
- Vollständige Auflösung aller HAFAS‑Referenzen:
  - betroffene Bahnhöfe
  - betroffene Linien / Produkte
  - betroffene Streckenabschnitte
  - zugehörige Ereignisse
- Anzeige der wichtigsten Informationen:
  - Titel, Beschreibung, Zeitraum
  - Priorität, Verbund, Produkt
  - vollständiger Text (HTML → Markdown)
- Sensor liefert:
  - Anzahl aktiver Störungen
  - Details zur ersten Störung
  - vollständige Liste aller Meldungen
- Dashboard‑kompatibel (Markdown, Entities, Custom Cards)
- HACS‑kompatibel

---

## 📦 Installation (HACS)

1. HACS öffnen  
2. Integrationen → Custom Repositories  
3. Repository hinzufügen:

   https://github.com/mgutsch42/nrw-rail-status  
   Typ: Integration

4. Integration installieren  
5. Home Assistant neu starten  
6. Integration hinzufügen:

   Einstellungen → Geräte & Dienste → Integration hinzufügen → „NRW Rail Status“

---

## 🧠 Funktionsweise

Die Integration nutzt die gleiche API wie die Webseite Zuginfo.nrw:

- HAFAS‑Version: 1.24
- Methode: HimSearch
- Region: NRW
- Client‑Emulation wie im Browser
- Session‑ID pro Request
- vollständige Referenzauflösung (locL, prodL, edgeL, eventL)
- asynchrone Kommunikation über aiohttp

Da die Zuginfo‑NRW‑Webseite mehrere Schutzmechanismen verwendet (Domain‑Trennung, Session‑Cookies, Header‑Fingerprinting), emuliert die Integration einen Browser‑ähnlichen Zugriff, um gültige Session‑Cookies zu erhalten.

---

## 🧩 Sensor‑Datenstruktur

Der Sensor sensor.nrw_rail_status_sensor liefert:

### State

- Anzahl aktiver Störungen

### Attribute

- first_id  
- first_title  
- first_text  
- first_start  
- first_end  
- first_priority  
- first_comp  
- first_product  
- first_active  
- first_locations  
- first_products  
- first_edges  
- first_events  
- messages (Liste aller Meldungen inkl. Referenzauflösungen)

---

## 📊 Beispiel‑Dashboard

title: NRW Rail Status  
icon: mdi:train  
cards:

  - type: entities  
    title: Übersicht  
    entities:  
      - entity: sensor.nrw_rail_status_sensor  
        name: Anzahl der Störungen  

  - type: markdown  
    title: Details zur ersten Störung  
    content: |
      {% set msgs = state_attr('sensor.nrw_rail_status_sensor', 'messages') %}
      {% if msgs %}
      {% set first = msgs[0] %}

      ### {{ first.title }}

      Beschreibung:  
      {{ first.text }}

      Beginn: {{ first.start_date }} {{ first.start_time }}  
      Ende: {{ first.end_date }} {{ first.end_time }}

      Priorität: {{ first.priority }}  
      Verbund: {{ first.comp }}  
      Produkt: {{ first.product }}

      Bahnhöfe:  
      {{ first.locations }}

      {% else %}
      Keine aktuellen Störungen.
      {% endif %}

---

## 🛠 Dateien & Architektur

custom_components/nrw_rail_status/  
│  
├── __init__.py          → Integration Setup  
├── api.py               → HAFAS‑API‑Client + NRWMessage  
├── coordinator.py       → UpdateCoordinator  
├── sensor.py            → Sensor‑Definition  
├── const.py             → Konstanten  
├── config_flow.py       → UI‑Konfiguration  
├── manifest.json        → HA‑Manifest  
└── translations/        → Lokalisierung  

---

## 🧪 Debugging & Entwicklungs‑Historie

Während der Entwicklung und Reverse‑Engineering‑Phase wurden mehrere technische Besonderheiten der Zuginfo‑NRW‑API identifiziert und behoben:

### ✔ Domain‑Konsistenz  
Die API akzeptiert Session‑Cookies nur, wenn alle Requests dieselbe Domain verwenden.  
Daher wurden alle www.zuginfo.nrw‑Einträge entfernt und auf https://zuginfo.nrw/ vereinheitlicht.

### ✔ Korrektur der Basis‑URLs  
Mehrere interne URLs (z. B. /gate/, /webapp/, /him/HimSearch) wurden bereinigt und auf die korrekte Domain umgestellt.

### ✔ Referer‑ und Origin‑Header  
Die API verweigert Session‑Cookies, wenn Referer/Origin nicht exakt zur Domain passen.  
Alle Header wurden entsprechend korrigiert.

### ✔ Session‑Handling  
Die Integration baut eine Browser‑ähnliche Session auf, um gültige Cookies zu erhalten.  
Dies umfasst:

- PRE‑Request auf /webapp/  
- vollständige Header‑Emulation  
- Cookie‑Persistenz über aiohttp  

### ✔ HTML‑Fallback‑Erkennung  
Falls der Server statt JSON eine Login‑Seite liefert, erkennt die Integration dies automatisch und protokolliert:

- fehlende Cookies  
- Content‑Type‑Mismatch  
- HTML‑Snippet zur Analyse  

Dies erleichtert das Debugging bei API‑Änderungen.

## 🧪 Erweiterte Debugging‑Historie & Testläufe

Um anderen Entwicklern die erneute Fehlersuche zu ersparen, dokumentiert dieser Abschnitt **alle bisherigen Testläufe**, **Hypothesen**, **Fehlerbilder** und **Erkenntnisse**, die während der Reverse‑Engineering‑Phase gesammelt wurden.

Diese Informationen sollen helfen, die Schutzmechanismen der Zuginfo.nrw‑HAFAS‑HIM‑API besser zu verstehen und zukünftige Lösungsansätze gezielt zu entwickeln.

---

### 🔍 1. Domain‑Konsistenz

**Hypothese:**  
Die API akzeptiert Cookies nur, wenn alle Requests dieselbe Domain verwenden.

**Tests:**  
- GET/POST auf `https://www.zuginfo.nrw/`  
- GET/POST auf `https://zuginfo.nrw/`  
- Mischung aus beiden Domains  

**Ergebnis:**  
- Cookies werden **nie** gesetzt, wenn Domains gemischt werden  
- Auch bei konsistenter Domain: **keine Cookies**  
- Domain‑Mismatch ist **nicht** die alleinige Ursache

---

### 🔍 2. Header‑Fingerprinting

**Hypothese:**  
Die API setzt Cookies nur, wenn bestimmte Browser‑Header exakt nachgebildet werden.

**Tests:**  
- Vollständige Chrome‑Header (Android)  
- Vollständige Chrome‑Header (Desktop)  
- Minimal‑Header (Accept, Origin, Referer)  
- Entfernen aller `Sec-*` Header  
- Entfernen von `Accept-Encoding`  
- Variation von `User-Agent`  

**Ergebnis:**  
- Falscher Referer → **immer** keine Cookies  
- Falscher Accept‑Header → **immer** keine Cookies  
- Korrekte Header → **trotzdem** keine Cookies  
- Fingerprinting ist **nicht** der einzige Blocker

---

### 🔍 3. Referer‑ und Origin‑Validierung

**Hypothese:**  
Die API akzeptiert nur Requests, die wie echte WebApp‑Requests aussehen.

**Tests:**  
- Referer: `/`  
- Referer: `/webapp/`  
- Origin: `https://www.zuginfo.nrw`  
- Origin: `https://zuginfo.nrw`  

**Ergebnis:**  
- Falscher Referer → sofortiger HTML‑Fallback  
- Richtiger Referer → kein HTML‑Fallback, aber **keine Cookies**  
- Origin spielt eine Rolle, ist aber nicht allein entscheidend

---

### 🔍 4. PRE‑Request auf `/webapp/`

**Hypothese:**  
Die WebApp initialisiert eine Session über einen GET‑Request.

**Tests:**  
- GET auf `/webapp/`  
- GET auf `/webapp/index.html`  
- GET auf `/`  

**Ergebnis:**  
- Keine Cookies werden gesetzt  
- PRE‑Request ist **notwendig**, aber **nicht ausreichend**

---

### 🔍 5. POST‑Request‑Analyse

**Hypothese:**  
Der Payload muss exakt dem WebApp‑Payload entsprechen.

**Tests:**  
- Payload aus DevTools übernommen  
- Payload minimalisiert  
- Payload mit anderen HAFAS‑Parametern  
- Variation von `hciVersion`, `hciClientVersion`, `aid`, `ext`, `l`, `v`  

**Ergebnis:**  
- Falscher Payload → HTML‑Fallback  
- Richtiger Payload → **keine Cookies**, aber auch kein HTML  
- Payload ist **nicht** der alleinige Blocker  
- Vermutlich zusätzliche serverseitige Validierung

---

### 🔍 6. Cookie‑Debugging

**Hypothese:**  
Cookies werden gesetzt, aber aiohttp speichert sie nicht.

**Tests:**  
- Cookie‑Jar‑Debugging vor/nach POST  
- Cookie‑Filterung auf Domain vs. Subdomain  
- Logging aller Set‑Cookie‑Header  

**Ergebnis:**  
- Server sendet **keine** Set‑Cookie‑Header  
- Problem liegt **nicht** in aiohttp  
- Cookies werden serverseitig **nicht erzeugt**

---

### 🔍 7. HTML‑Fallback‑Erkennung

**Hypothese:**  
Der Server liefert HTML statt JSON, wenn die Session ungültig ist.

**Tests:**  
- Prüfung von `Content-Type`  
- Prüfung auf `<html>` im Response‑Body  
- Logging der ersten 500 Zeichen  

**Ergebnis:**  
- HTML‑Fallback tritt nur bei falschem Referer auf  
- Bei korrekten Headern → **kein HTML**, aber **keine Cookies**  
- Server akzeptiert Request formal, aber verweigert Session

---

### 🔍 8. Vermutete Schutzmechanismen

Basierend auf allen Tests sind folgende Mechanismen wahrscheinlich:

- **Browser‑Fingerprinting** (Header‑Kombinationen, UA‑Patterns)  
- **TLS‑Fingerprinting** (Cipher Suites, JA3‑Hash)  
- **Request‑Timing‑Analyse** (PRE → POST Sequenz)  
- **Client‑Token‑Generierung** (JS‑seitig)  
- **Anti‑Bot‑Mechanismen** (Rate‑Limits, Heuristiken)  

Diese Mechanismen sind typisch für moderne HAFAS‑Installationen.

---

### 📌 Zwischenfazit

Trotz vollständiger Nachbildung:

- der Domain  
- der Header  
- des Referers  
- des Origins  
- des Payloads  
- der Request‑Sequenz  
- der Browser‑Emulation  

setzt der Server **keine Session‑Cookies**.

Damit ist ein vollwertiger API‑Zugriff derzeit **nicht möglich**.

---

### 🧭 Nächste Schritte (für zukünftige Entwickler)

- Analyse des TLS‑Fingerprints (JA3)  
- Replay echter Browser‑Requests über Proxy  
- Nutzung eines Headless‑Browsers (Playwright/Selenium)  
- Untersuchung der JS‑Token‑Generierung  
- Vergleich der Request‑Sequenz mit HAR‑Export  
- Prüfung auf serverseitige Bot‑Detection  

---

## ⚠️ Aktueller Status der Integration

Diese Integration befindet sich derzeit in einem **experimentellen Zustand** und kann **keine funktionierenden Daten** von Zuginfo.nrw abrufen.

### Hintergrund

Die Webseite Zuginfo.nrw verwendet mehrere Schutzmechanismen, die eine automatisierte Abfrage verhindern:

- strikte Domain‑Konsistenz  
- Session‑Cookies, die nur unter bestimmten Header‑Kombinationen gesetzt werden  
- Browser‑Fingerprinting  
- HTML‑Login‑Fallback bei ungültiger Session  

Trotz vollständiger Nachbildung der bekannten Browser‑Header und korrekter Domain‑Konfiguration liefert der Server weiterhin:

- keine Session‑Cookies  
- HTML‑Login‑Seiten statt JSON  
- keine verwertbaren HIM‑Daten  

### Konsequenz

Der Sensor sensor.nrw_rail_status_sensor zeigt daher aktuell:

- 0 Störungen  
- keine Meldungen  
- keine Daten aus der API  

### Ziel

Die Integration bleibt bestehen, bis eine stabile Möglichkeit gefunden wird, eine gültige Session aufzubauen oder Zuginfo.nrw die API‑Mechanik ändert.  
Bis dahin dient das Projekt als technische Referenz und Dokumentation der HAFAS/HIM‑Struktur von Zuginfo.nrw.

---

## 🤝 Beiträge & Community

Beiträge sind ausdrücklich willkommen!

- Siehe **CONTRIBUTING.md** im gleichen Verzeichnis wie diese README  
- Fehler melden: GitHub → *Issues*  
- Ideen, Fragen, Diskussionen: GitHub → *Discussions*  

Jede Unterstützung hilft, die Integration langfristig funktionsfähig zu machen.

---

## 📄 Lizenz

MIT License

---

## ❤️ Autor
Martin Gutsch  
GitHub: https://github.com/mgutsch42
