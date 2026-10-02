# Interaktiv festgelegter Umfang — 2. Oktober 2026

| Bereich | Entscheidung |
|---|---|
| Grundlage | MicroPython, gesamte Bewässerung auf dem ESP |
| Board | diymore ESP32-NodeMCU / ESP-WROOM-32, USB-C / CH340 (Produktbild) |
| Hardware | 2 Pflanzen, je Sensor/Pumpe; 5 V; Relaislogik noch unbekannt |
| Sensoren | Kapazitiv analog; gemeinsamer Tank mit HC-SR04 |
| Automatik | Nur Bodenfeuchtigkeit; Portionen mit Einwirkpause |
| Pumpen | Immer nur eine gleichzeitig |
| Mengen | ml über Pumpenkalibrierung |
| Tank | Prozent und Liter; Form offen, Messpunktkalibrierung |
| Reserve | Ansauggrenze beim Einrichten bestimmen |
| Auffüllen | Automatische Freigabe nach stabiler Messung |
| Keine Feuchtezunahme | Kanal sperren und melden |
| Schutz | Zyklus/24h je Kanal plus Gesamtlimit; auch manuell |
| Neustart | Sicherheitspause; keine laufende Portion wiederaufnehmen |
| Globaler Stopp | Dauerhafte Sperre bis zur manuellen Freigabe |
| Oberfläche | Vollständige Verwaltung, keine LAN-Anmeldung |
| Einrichtung | Geführter Assistent, komplett neue Konfiguration |
| Startwerte | Im Assistenten nach Kalibrierung festlegen |
| Profile | Anpassbare Startwerte |
| Verlauf | 24 Stunden plus Ereignisse |
| Integration | Optional MQTT Discovery / Home Assistant |
| Meldungen | Home Assistant übernimmt Push/Telegram |
| Updates | USB und WLAN |
| Lokale Bedienung | Nur Browser, kein Display/Taster |

Vor dem echten Anschluss noch nötig: Relaislogik, tatsächliche GPIO-Verdrahtung,
Tankabstände/Litermesspunkte und Fördermengen.
