# Smart Irrigation 4 — eigenständiger Neubau

**Entwurfsstand: Steuerung am PC getestet, noch nicht auf dem tatsächlichen ESP32 geprüft.**
Die bisherige Version bleibt unter `aktuell/` erhalten. V4 startet mit einer neuen Konfiguration.

Vereinbart: MicroPython, zwei kapazitive analoge Bodensensoren, zwei 5-V-Pumpen an Relais,
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
Die Oberfläche auf dem ESP entspricht `firmware/index.html`.

```bash
python3 -m unittest discover -s rebuild/tests -v
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

Mit `make_bundle.py` ein vollständiges Paket erzeugen und unter „System & Updates“ hochladen.
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
