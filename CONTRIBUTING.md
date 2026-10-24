# Am Projekt mitarbeiten

Die aktive Entwicklung findet in `rebuild/` statt. `aktuell/` enthält die erhaltene V3. Bitte bei Fehlerberichten und Änderungen die betroffene Version angeben.

## Orientierung

| Pfad | Aufgabe |
|---|---|
| `rebuild/firmware/` | MicroPython-Anwendung, Steuerung, MQTT und HTTP. |
| `rebuild/ui/index.html` | Bearbeitbare Quelle der Weboberfläche. |
| `rebuild/tools/` | Erzeugung der Webdateien, Installation, Anwendungsupdate und Simulation. |
| `rebuild/tests/` | Python- und Browser-Prüfungen. |
| `rebuild/preview.html` | Erzeugte Browser-Demo mit Beispieldaten. |
| `rebuild/home_assistant/` | Benachrichtigungsbeispiel für V4. |

## Änderungen an der Oberfläche

Die Quelle `rebuild/ui/index.html` bearbeiten. Getrennte CSS-/JavaScript-Dateien, gzip-Dateien und Demo werden daraus erzeugt. Erzeugte Dateien und Updatepaket nach einer Änderung gemeinsam aktualisieren:

```powershell
python rebuild/tools/build_assets.py
python rebuild/tools/make_bundle.py
```

## Lokal prüfen

Für die PC-Prüfungen Python 3.12 oder neuer und Node.js 24 verwenden. Alle Befehle laufen im Stammverzeichnis des Repositorys:

```powershell
python -m compileall -q rebuild/firmware rebuild/tools aktuell
python -m unittest discover -s rebuild/tests -v
npm ci --prefix rebuild --ignore-scripts
npm test --prefix rebuild
python rebuild/tools/simulate.py
```

Diese Prüfungen ersetzen keine Prüfung der tatsächlichen Relais, Versorgung oder Sensoren. Einen Hardwaretest mit Board, Firmwarestand, Aufbau und beobachtetem Ergebnis dokumentieren.

## Fehlerberichte und Pull Requests

Ein kleiner, nachvollziehbarer Fehlerbericht hilft: Version, betroffener Bereich, Schritte, erwartetes Verhalten und tatsächliche Meldung. Zugangsdaten und private Sicherungen vor dem Teilen entfernen. Bei Änderungen an der Bewässerungslogik auch Auswirkungen auf Tankreserve, Stoppsperre und Mengenlimits beschreiben.

WLAN-/MQTT-Zugangsdaten, Laufzeitzustände und `rebuild/usb-backup/` bleiben lokal. Versionsnummern nur bei einer geplanten Veröffentlichung ändern; eine reine Dokumentationsänderung benötigt kein Firmware-Release.
