# Mit V4 loslegen

[Projekt](../README.md) · [Dokumentation](README.md) · [Verkabelung](../rebuild/docs/VERKABELUNG.md)

## Zuerst den passenden Installationsweg wählen

V4 liegt vollständig unter `rebuild/`. Der Installer im Stammverzeichnis gehört zu V3. Alle folgenden Befehle werden im Stammverzeichnis des Repositorys ausgeführt. `COM8` durch den tatsächlichen USB-Port ersetzen, unter Linux beispielsweise `/dev/ttyUSB0`.

Vor USB-Installation oder Änderungen an der Verdrahtung die Pumpenversorgung physisch trennen. MicroPython muss bereits passend zum Board installiert sein. Die [Hardwareanleitung](../rebuild/docs/HARDWARE.md) beschreibt die Voraussetzungen.

## Neuinstallation oder Wechsel von V3

Das ist eine frische V4-Installation: WLAN, Kalibrierungen und Einstellungen werden neu eingerichtet. Der Installer sichert vorhandene Konfiguration und Startdateien lokal unter `rebuild/usb-backup/`.

```powershell
python -m pip install mpremote
python rebuild/tools/install.py COM8 --pump-power-disconnected
```

1. Mit dem Setup-WLAN `Irrigation-xxxxxx` verbinden und `http://192.168.4.1` öffnen.
2. Heim-WLAN und Gerätebezeichnung im Assistenten einrichten. Danach die vom Router vergebene Geräteadresse öffnen.
3. Board, Pins und Relaispolarität am tatsächlichen Aufbau prüfen und bestätigen; Automatik ausgeschaltet lassen.
4. Bodenfeuchtigkeit mit trockenen und nassen Referenzwerten kalibrieren.
5. Tank mit leer/halbvoll/voll sowie Reserve- und Freigabegrenze kalibrieren. Der Sensor muss fest auf die Wasseroberfläche gerichtet sein.
6. Nach abgeschlossener elektrischer Prüfung die Fördermenge jeder Pumpe mit einem Messbecher bestimmen. Nur vollständig beendete Messläufe übernehmen.
7. Portionen, Einwirkzeit und Mengenlimits einstellen. Erst nach beobachtetem Probelauf die Automatik freigeben.

Nach dem Neustart gilt eine Startpause. Die Oberfläche zeigt an, welche Voraussetzung eine Bewässerung gegebenenfalls noch sperrt.

## Bestehende V4.0.0 / V4.0.1 aktualisieren

Der bisherige WLAN-Updater erwartet neun Textdateien und kann das neue Paket mit komprimierten Webdateien noch nicht verarbeiten. Für den einmaligen Wechsel auf V4.0.2 den USB-Anwendungsupdateweg verwenden:

```powershell
python -m pip install mpremote
python rebuild/tools/app_update.py COM8 --pump-power-disconnected
```

Das Werkzeug sichert Konfiguration, Wasserbudgets und Startdateien lokal und erhält die bestehenden V4-Einstellungen. Die Sicherung enthält private Daten und bleibt aus Git ausgeschlossen. Dieser Migrationsweg wurde am PC geprüft; der reale Durchlauf auf Hardware steht noch aus.

## WLAN-Updates ab V4.0.2

Das vollständige JSON-Paket aus den [GitHub Releases](https://github.com/JannWdl/ESP32-SmartIrrigation/releases/latest) herunterladen und in „System & Updates“ auswählen. Während des Updates ist die Steuerung gesperrt. Dateien werden auf Größe und SHA-256 geprüft; die vorherige Anwendung bleibt für den Start-Rollback erhalten. Vor weiteren Updates freien Flash prüfen.

## Home Assistant ergänzen

Die lokale Automatik funktioniert auch ohne Home Assistant. Für zusätzliche Anzeige und Bedienung [MQTT Discovery einrichten](HOME_ASSISTANT_V4.md).

## Wenn eine Portion nicht startet

Den angezeigten Status prüfen: Tankreserve oder ungültiger Abstand, aktive Startpause, globale Stoppsperre, fehlende Kalibrierung, nicht bestätigte Ausgänge oder verbrauchtes Budget können den Start verhindern. Eine gedrückte HA-Taste allein bestätigt keine gelaufene Pumpe; maßgeblich sind Geräte-Status und Ereignisverlauf.

Ausführliche Beschreibung: [V4-Betrieb und Wasserbudgets](../rebuild/README.md).
