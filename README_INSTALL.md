# Installation auf dem ESP32

## Schnellstart

Normales Update ohne erneutes Flashen:

```powershell
python install.py COM8 --skip-flash
```

Ohne Port fragt der Installer danach:

```powershell
python install.py
```

## Nur Dateien kopieren

Empfohlen für normale Updates:

```powershell
python install.py COM8 --skip-flash
```

## MicroPython neu flashen

Firmware-Datei vorher lokal herunterladen, dann:

```powershell
python install.py COM8 --bin firmware.bin
```

Der Installer löscht dann den ESP32-Flash und flasht die angegebene Firmware.

## Projektordner explizit angeben

```powershell
python install.py COM8 --skip-flash --project-dir aktuell
```

## Wenn `could not enter raw repl` kommt

1. ESP32 per **EN/RESET** neu starten.
2. Direkt danach nochmal ausführen:

```powershell
python install.py COM8 --skip-flash
```

3. Falls es weiter hängt: ESP32 vom Strom trennen, wieder verbinden, direkt erneut starten.

Der Installer sendet vor dem Kopieren automatisch `Ctrl+C`, damit eine laufende `main.py`/Webserver-Schleife unterbrochen wird.

## Was wird nicht auf den ESP kopiert?

Der Installer kopiert keine Home-Assistant-Dateien, keine Docs und keine veralteten Telegram-Direct-Dateien auf den ESP32.
