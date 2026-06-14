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
