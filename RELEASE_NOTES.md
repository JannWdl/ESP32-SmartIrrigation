# Release Notes · V4.0.2

Veröffentlicht am 24. Oktober 2026 · [Release und Updatepaket](https://github.com/JannWdl/ESP32-SmartIrrigation/releases/tag/v4.0.2)

## Was neu ist

- V4 ist mit dem bisherigen Hauptstand zusammengeführt. Die V3-Firmware und Beispiele bleiben unter `aktuell/` erhalten.
- Die Weboberfläche lädt komprimierte, versionierte Dateien und nutzt den Browser-Cache. Einstellungen und Verlauf werden bei Bedarf geladen; in unsichtbaren Tabs pausieren Hintergrundabfragen.
- WLAN-Energiesparmodus ist deaktiviert. Wiederholte MQTT-Fehler führen bei inaktiven Pumpen zu einer erneuten Netzwerkverbindung.
- Der Tank lässt sich mit drei Füllstandspunkten kalibrieren. Die Fördermengenkalibrierung akzeptiert bestätigte, vollständig beendete Messläufe.
- Updatepakete enthalten alle Webdateien. Das USB-Anwendungsupdate erhält bestehende V4-Einstellungen und Wasserbudgets.

## Der richtige Updateweg

| Bisheriger Stand | Vorgehen |
|---|---|
| V3 oder neues Gerät | V4 frisch installieren und neu einrichten. |
| V4.0.0 / V4.0.1 | Einmaliges USB-Anwendungsupdate; das bisherige Neun-Dateien-WLAN-Format unterstützt das neue Paket noch nicht. |
| Ab V4.0.2 | Vollständiges JSON-Paket über „System & Updates“ einspielen. |

[Schritte und Befehle](docs/GETTING_STARTED.md)

## Prüfstand

44 Python-Tests, Browser-Tests, Syntaxprüfung und Offline-Simulation wurden erfolgreich ausgeführt. Die Web- und Netzwerkoptimierungen wurden mit der zugrunde liegenden V4.0.1 auf einem ESP32 geprüft. Das vollständige V4.0.2-Paket und der USB-Migrationsweg wurden noch nicht erneut auf Hardware durchlaufen.

## Frühere Versionen

[V3.9-Release Notes](docs/legacy/RELEASE_NOTES_3.9.md) · [Gesamtes Changelog](CHANGELOG.md)
