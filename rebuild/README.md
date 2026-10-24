# Smart Irrigation 4 · technische Dokumentation

[Projektstartseite](../README.md) · [Erste Schritte](../docs/GETTING_STARTED.md) · [Home Assistant](../docs/HOME_ASSISTANT_V4.md)

**Version 4.0.2:** Steuerung und Updatepakete am PC geprüft. Weboberfläche, HTTP-Optimierungen und WLAN/MQTT-Anbindung wurden mit der zugrunde liegenden 4.0.1-Anwendung auf einem ESP32 getestet. Die zusammengeführte 4.0.2-Ausgabe einschließlich USB-Migrationswerkzeug wurde nicht erneut auf das Gerät übertragen.
Die bisherige V3 bleibt unter `aktuell/` erhalten. Eine V4-Neuinstallation beginnt mit neuen Einstellungen; das USB-Anwendungsupdate erhält bestehende V4-Einstellungen.

Die Referenzkonfiguration verwendet MicroPython, zwei kapazitive analoge Bodensensoren, zwei 5-V-Pumpen an Relais,
ein gemeinsamer Tank mit HC-SR04, vollständige lokale Weboberfläche, optionale MQTT-Anbindung.
Board anhand des Produktbildes: diymore ESP32-NodeMCU / ESP-WROOM-32, USB-C, CH340.
Relais laut Produktbild: AYWHP 3-V-Einkanalmodule mit High-Level-Trigger.
Vorbelegung: HIGH = ein / LOW = aus (`active_low: false`).
Bis zur Prüfung des tatsächlichen Moduls bleiben Pumpenausgänge gesperrt.
Vorbelegung: Sensoren GPIO34/35, Relais GPIO27/26, HC-SR04 Trigger GPIO18 / Echo GPIO19.

## Verkabelung

[Anleitung mit Schaltbildern, allen Anschlusslisten und Ersttest](docs/VERKABELUNG.md)

Der Plan umfasst getrennte Versorgungsschienen, gemeinsame Masse, Echo-Spannungsteiler,
COM/NO-Pumpenkreise, Freilaufdioden und die Prüfung ohne laufende Pumpen.
Netzteil/Sicherung/Leitungen anhand der tatsächlichen Pumpenströme auswählen;
Relais-Modulversorgung und Bodensensor-Kompatibilität vor Anschluss bestätigen.

## Funktionen

- Lokale Automatik nach Bodenfeuchtigkeit, auch ohne WLAN/MQTT/Home Assistant.
- Wasserportionen in ml über gemessene Fördermenge; anschließende Einwirkzeit und erneute Messung.
- Immer genau eine Pumpe, keine Warteschlange für wiederholte manuelle Befehle.
- Tankfüllstand in Prozent und geschätzten Litern über frei eingegebene Kalibrierpunkte.
- Tankreserve oder ungültige/veraltete Messung stoppt/sperrt Pumpen. Drei stabile Messungen
  unterhalb des Freigabeabstands erlauben das automatische Fortsetzen nach Auffüllen.
- Laufzeit-, Zyklus- und 24-Stunden-Limits je Kanal plus gemeinsames Mengenlimit.
- Drei Portionen ohne ausreichende Feuchtezunahme sperren den Kanal bis zur manuellen Prüfung.
- „Alles stoppen“ schaltet ab und sperrt die Automatik dauerhaft bis zur Freigabe.
- Sicherheitspause nach Neustart; Pumpen sind ausgeschaltet. Bewässerung wird nicht fortgesetzt.
- Einrichtungsassistent mit WLAN, GPIO-Prüfung, Boden-, Tank- und Pumpenkalibrierung.
- Anpassbare Pflanzenprofile als Startwerte; keine universell gültigen Feuchteempfehlungen.
- 24 Stunden Messwertverlauf im RAM (5-Minuten-Raster) plus 40 Ereignisse; Neustart leert Verlauf.
- MQTT Discovery, Status/Fehler, Portionstasten, Auto-Schalter, globaler Stopp/Freigabe.
- USB-Erstinstallation sowie vollständige, SHA-256-geprüfte WLAN-Updates mit Start-Rollback.

## Vorschau und Tests

`preview.html` im Browser öffnen: **Beispieldaten, keine echte Pumpensteuerung**.
Die bearbeitbare Oberfläche liegt in `ui/index.html`. `tools/build_assets.py` erzeugt daraus `firmware/index.html`, versionierte CSS-/JavaScript-Dateien, gzip-Dateien und die eigenständige Demo `preview.html`.

```bash
python3 rebuild/tools/build_assets.py
python3 -m unittest discover -s rebuild/tests -v
npm ci --prefix rebuild --ignore-scripts
npm test --prefix rebuild
python3 rebuild/tools/simulate.py
python3 rebuild/tools/make_bundle.py
```

## USB-Erstinstallation

MicroPython passend zum tatsächlichen Board installieren. V4 benötigt `machine`, `network`,
`asyncio`, `json`, `hashlib`, `binascii` und `os`; keine umqtt/urequests-Abhängigkeit.
**Pumpenversorgung physisch trennen**, bevor die bisherige Installation ersetzt wird.

```bash
python -m pip install mpremote
python rebuild/tools/install.py COM8 --pump-power-disconnected
```

Der Installer sichert vorhandene Konfiguration/Startdateien in `rebuild/usb-backup`, installiert die
neue Anwendung und beginnt absichtlich mit neuen Einstellungen. WLAN und bisherige Kalibrierungen
werden nicht übernommen. Mit `Irrigation-xxxxxx` verbinden, `http://192.168.4.1` öffnen.
Bei erfolgreicher Heim-WLAN-Verbindung endet das Setup-WLAN. Bei Ausfall wird es wieder aktiviert.
Ein optionales Setup-WLAN-Passwort lässt sich im Assistenten setzen. Es gibt keine Anmeldung im LAN.

Hardware/Tank zunächst speichern (Automatik aus). Nach Neustart und Startpause die Bodenwerte prüfen,
kalibrieren, Pumpenausläufe in Messbecher führen und Fördermengen übernehmen. Anschließend
Portionen/Limits passend zu den tatsächlichen Pflanzen einstellen und Automatik aktivieren.
Bis alle Bedingungen erfüllt sind, wird eine Bewässerung abgelehnt.

## Wasserbudgets und Kalibrierung

Mengen sind **Schätzwerte** aus ml/s und Laufzeit, keine Durchflussmessung. Vor Einschalten wird
jede vollständige Portion dauerhaft reserviert. Ein vorzeitiger Stopp gibt diese Reserve nicht zurück.
Ein Kalibrierlauf (0,5–5 s) reserviert konservativ das volle Zykluslimit im Tagesbudget, weil die
Fördermenge noch unbekannt ist. Tankreserve, Ausgangsbestätigung, Startpause, Tages- und Laufzeitlimits
bleiben dabei aktiv. Ein noch nicht kalibrierter Bodensensor verhindert nur Automatik/Handbewässerung,
nicht den ausdrücklich gestarteten Messbecher-Kalibrierlauf. Ein echter Bodensensorfehler sperrt auch ihn.

„Tag“ bedeutet hier ein konservatives **24-Stunden-Budget aktiver Betriebszeit**, nicht Mitternacht.
Ohne sichere Echtzeituhr wird ausgeschaltete Zeit nicht zur Budgetfreigabe gezählt. Der Zähler wird
alle 10 Minuten und bei jeder Mengenreservierung/Sperränderung gespeichert. Neustarts geben daher
keine zusätzlichen Wassermengen frei; kleine verlorene Zeitintervalle verzögern die Freigabe.

## WLAN-Updates

Mit `make_bundle.py` das vollständige Paket `smart-irrigation-4.0.2.json` erzeugen und unter „System & Updates“ hochladen.
Die Steuerung wird dabei gesperrt. Dateien landen in einem neuen Releaseverzeichnis; Name,
Größe und SHA-256 werden geprüft. Erst danach wird der Release-Zeiger atomar per Zweitslot gespeichert.
Ein fehlgeschlagener Start führt beim nächsten Boot zur vorherigen Anwendung zurück.
Der stabile Bootstrap wird ausschließlich über USB aktualisiert. Alte Releases werden aus
Sicherheitsgründen nicht automatisch gelöscht; vor weiteren Updates freien Flash prüfen.
Die Prüfsummen schützen vor beschädigten Uploads, **nicht** vor böswillig erstellten Paketen.
Nur selbst erzeugte/vertraute Pakete verwenden. HTTP/MQTT sind für das eigene LAN vorgesehen.

## Noch auf Hardware zu prüfen

Boardbezeichnung, Pins, Relaispolarität, sichere Ausgangspegel beim Einschalten/Reset,
HC-SR04-Pegelwandlung und tatsächliche Messabstände, Pumpenfördermengen, Netzteil/Entstörung,
WLAN-Wechsel, MQTT-Reconnect, Flashgröße und Update-Rollback. Details: `docs/HARDWARE.md`.
Die softwareseitige Abschaltung ist kooperativ, mit begrenzten Netzwerk-Wartezeiten und Watchdog;
sie ersetzt keine elektrische Absicherung oder garantierte Hardwareabschaltung.


## Bestehende V4-Einstellungen behalten

Die bisherigen 4.0.0/4.0.1-Updater erwarten genau neun Textdateien. Ein Paket mit getrennten,
komprimierten Webdateien darf dort nicht direkt eingespielt werden. Für den einmaligen Wechsel
auf 4.0.2 gibt es einen USB-Anwendungsupdatepfad:

```bash
python -m pip install mpremote
python rebuild/tools/app_update.py COM8 --pump-power-disconnected
```

Vorher die Pumpenversorgung physisch trennen. Das Werkzeug prüft die vorhandenen Release-Zeiger,
sichert verfügbare Konfiguration, Budgets und Startdateien unter `rebuild/usb-backup/`, überträgt
alle Anwendungsdateien in ein neues Release und vergleicht SHA-256-Prüfsummen. Konfiguration,
Wasserbudgets und Bootstrap bleiben erhalten. Der bestehende Start-Rollback bleibt aktiv.
Diese Sicherungen enthalten private Einstellungen und werden von Git ausgeschlossen.
Die USB-Migration wurde am PC geprüft; ein realer Migrationsdurchlauf mit diesem Werkzeug steht aus.
Ab 4.0.2 enthalten die WLAN-Pakete alle Webdateien; binäre gzip-Dateien werden im Paket als Base64
transportiert und im Browser vor dem Upload dekodiert. Künftige Asset-Prüfsummen dürfen wechseln.
`tools/install.py` bleibt die ausdrücklich frische Installation mit neuen Einstellungen.

## Webleistung und Verbindungsstabilität

- Vorab komprimierte Webdateien, langfristiger Browser-Cache für versionierte CSS-/JavaScript-Dateien
  und ETag-Prüfung der Startseite. Der ESP komprimiert keine Dateien während der Anfrage.
- Kompakte Übersicht statt vollständiger Einstellungen beim Öffnen. Einstellungen und Verlauf
  werden bei Bedarf geladen. Hintergrundabfragen pausieren bei unsichtbarer Seite.
- Status im Leerlauf alle fünf statt drei Sekunden; während einer Pumpenaktivität häufiger.
  Ereignisverlauf und Diagrammdaten werden im sichtbaren Verlauf höchstens alle 15 Sekunden geladen.
- Wiederverwendbarer 1-KB-Dateipuffer, kompakte JSON-Ausgabe und begrenzte Antwortgrößen.
- WLAN-Energiesparmodus aus; nach wiederholten MQTT-Fehlern Wiederverbindung bei inaktiver Pumpe.
  Während der Netzwerkumschaltung verhindert der Wartungszustand neue Pumpenstarts.
- Tankkalibrierung mit Messpunkten für leer/halbvoll/voll und optionaler Literangabe.
  Fördermengenkalibrierung lässt nur bestätigte, vollständig beendete Messläufe übernehmen.

In einer Messung der HTTP-Datenabrufe inklusive erster Statusanzeige: bisher etwa 5,4 s,
mit optimierten Dateien etwa 3,5 s, mit gefülltem Browser-Cache etwa 2,0 s. Beim ersten Öffnen
wurden rund 62 % weniger Nutzdaten übertragen. Das sind einzelne Messungen im lokalen WLAN;
parallele Browserabfragen und Funkbedingungen beeinflussen die Werte. Die tatsächliche
Bildschirmdarstellung wurde zusätzlich im Browser geprüft, aber nicht zeitlich vermessen.
Die Weboptimierung verändert keine Pumpenlimits oder Tank-Schutzgrenzen.
