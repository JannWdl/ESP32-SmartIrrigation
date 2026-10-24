# Changelog

## 4.0.2 – 24.10.2026

- V4 mit dem bisherigen Hauptstand zusammengeführt; V3 unter `aktuell/` einschließlich optionaler DHT11-/HC-SR04-Erweiterungen erhalten.
- Optimierte Weboberfläche mit gzip, versionierten Browser-Dateien, Cache-Prüfung und bedarfsgesteuerten Abfragen.
- WLAN-Energiesparmodus deaktiviert und sichere Wiederverbindung nach wiederholten MQTT-Fehlern.
- Drei-Punkt-Tankkalibrierung und bestätigte Fördermengen-Messläufe.
- Vollständige Updatepakete einschließlich binärer Webdateien und USB-Anwendungsupdate mit Erhalt der Einstellungen.
- Zusätzliche HTTP-, Paket- und Browser-Prüfungen in der CI; keine lokalen Zugangsdaten veröffentlicht.

## v3.9.0

- GitHub-README ergänzt.
- Release Notes ergänzt.
- Home-Assistant-Setup-Doku ergänzt.
- Telegram-Tutorial inklusive BotFather `/setcommands` ergänzt.
- Telegram-Bot-Automationen auf `chat_id` statt `target` migriert.
- Legacy Telegram Notify Beispiel entfernt.
- Statusmeldung auf echte MQTT-Discovery-Entity-IDs angepasst.
- Veraltete ESP-Telegram-Direct-Dateien aus dem Projektordner entfernt.
- `version.json` aktualisiert.

## v3.8.0

- Home-Assistant-Paket und HACS-Vorlage ergänzt.
- MQTT-Updateintervall als HA Number-Entity ergänzt.
- RAM-/Stabilitätsanpassungen am ESP-Projekt.

## v3.7.1

- Installer ergänzt.
- HACS-/Custom-Integration-Vorlage ergänzt.

## v3.7.0

- Telegram Direct vom ESP entfernt/deaktiviert.
- Telegram über Home Assistant MQTT Proxy vorbereitet.
- MQTT-Command-Topics ergänzt.
- MQTT-Updateintervall im Webinterface ergänzt.
