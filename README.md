NRW Rail Status – Home Assistant Integration
⚠️ Aktueller Status
Die bisherige Datenquelle (Zuginfo.nrw / HIM‑API) liefert seit einer API‑Änderung keine stabilen oder vollständigen Daten mehr.
Die Integration funktioniert technisch, aber die API liefert:

HAMM‑Fehler

leere oder unvollständige JSON‑Antworten

abweichende Strukturen gegenüber bekannten HAFAS/HIM‑Implementierungen

Das Projekt befindet sich daher aktuell in einer Analyse‑ und Übergangsphase.

👉 Aktueller Stand & Diskussion:
https://github.com/mgutsch42/nrw-rail-status/issues/2

🤝 Hinweis für Contributor
Dieses Projekt ist ein Community‑Projekt.
Ich selbst bin kein Experte für HAFAS/HIM‑APIs oder Reverse‑Engineering und lerne vieles gerade erst kennen.

Ich kann:

das Projekt koordinieren

testen

dokumentieren

die Integration weiterentwickeln

Aber ich bin auf fachliche Unterstützung bei der API‑Analyse angewiesen.

Kurz gesagt:  
Ich bringe Struktur, Motivation und die Integration selbst mit —
die Community bringt das API‑Know‑how mit.

Jede Hilfe ist willkommen: Hinweise, Tests, Logs, Code.

🚆 Funktionsumfang
Live‑Abruf der NRW‑HIM‑API (HimSearch)

Anzeige der aktuellen Anzahl von Störungen

Detailinformationen zur ersten Störung

Vollständige Liste aller Meldungen (Titel, Text, Zeitraum, Priorität, Verbund)

Automatische Aktualisierung über einen Update‑Coordinator

100% kompatibel mit Standard‑Home‑Assistant‑Karten

📦 Installation über HACS (manuell)
HACS → Integrationen

Rechts oben: Custom repositories

Folgende URL eintragen:

Code
https://github.com/mgutsch42/nrw-rail-status
Typ: Integration

Repository hinzufügen

Integration installieren

Home Assistant neu starten

Integration hinzufügen: NRW Rail Status

⚙️ Konfiguration
Die Integration nutzt einen Config‑Flow, es ist keine YAML‑Konfiguration notwendig.

Nach der Einrichtung erscheint ein Sensor:

Code
sensor.nrw_rail_status_sensor
🧠 Sensor‑Daten
State
Anzahl der aktiven Störungen

Attribute
first_title – Titel der ersten Meldung

first_text – Beschreibung (Markdown)

first_start – Startzeitpunkt

first_end – Endzeitpunkt

first_priority – Priorität

first_comp – Verbund (z. B. VRR, NWL)

first_product – Produktklasse

first_id – Meldungs‑ID

messages – Liste aller Meldungen als strukturierte Objekte

📊 Beispiel‑Dashboard (Standard‑HA‑Karten)
yaml
title: NRW Rail Status
icon: mdi:train
cards:

  - type: entities
    title: Übersicht
    entities:
      - entity: sensor.nrw_rail_status_sensor
        name: Anzahl der Störungen

  - type: entity
    entity: sensor.nrw_rail_status_sensor
    name: Statusanzeige
    state_color: true

  - type: markdown
    title: Details zur ersten Störung
    content: |
      {% set s = states('sensor.nrw_rail_status_sensor') | int %}
      {% set first = state_attr('sensor.nrw_rail_status_sensor', 'messages')[0] if s > 0 else None %}

      **Aktuelle Störungen:** {{ s }}

      {% if s > 0 %}
      **Titel:** {{ first.title }}

      **Beschreibung:**  
      {{ first.text }}

      **Beginn:** {{ first.start }}  
      **Ende:** {{ first.end }}

      **Priorität:** {{ first.priority }}  
      **Verbund:** {{ first.comp }}  
      **Produkt:** {{ first.product }}  
      **Meldungs-ID:** {{ first.id }}
      {% else %}
      Keine aktuellen Störungen gemeldet.
      {% endif %}

  - type: markdown
    title: Alle Störungen
    content: |
      {% set msgs = state_attr('sensor.nrw_rail_status_sensor', 'messages') %}
      {% if msgs %}
      {% for m in msgs %}
      ---
      ### **{{ m.title }}**
      **Beschreibung:**  
      {{ m.text }}

      **Beginn:** {{ m.start }}  
      **Ende:** {{ m.end }}

      **Priorität:** {{ m.priority }}  
      **Verbund:** {{ m.comp }}  
      **Produkt:** {{ m.product }}  
      **ID:** {{ m.id }}

      {% endfor %}
      {% else %}
      Keine Störungen vorhanden.
      {% endif %}
🧩 Technische Details
Die Integration basiert auf:

Config Flow — UI‑basierte Einrichtung

DataUpdateCoordinator — zyklische API‑Abfrage

Sensor‑Plattform — strukturierte Attribute

Logging — Debug‑Ausgaben

Asynchronem HTTP‑Client (aiohttp)

Der technische Unterbau ist stabil — es fehlt lediglich eine zuverlässige Datenquelle.

🧪 Was bereits getestet wurde
direkte API‑Abfragen über Browser, Postman und aiohttp

GET‑ und POST‑Varianten der HIM‑Endpunkte

Parameter wie format=json, limit, filter

Analyse der Netzwerk‑Requests der NRW‑Webseite

Vergleich mit HAFAS/HIM anderer Verkehrsverbünde

Debug‑Logging der Integration

Tests alternativer Datenquellen (VRR, NVR, NWL, DB, GTFS‑RT)

Ergebnis:  
Die API liefert derzeit keine stabile, verwertbare Struktur.

📄 Lizenz
Wird später ergänzt.
