# ESP32-Bodenfeuchtigkeit-HA / Smart Irrigation

ESP32-basierte Bewässerungssteuerung mit Weboberfläche, mehreren Pumpen-/Sensor-Kanälen, MQTT und Home-Assistant-Discovery.

Diese Version ist bewusst **ohne Telegram direkt auf dem ESP32**, weil Telegram-HTTPS/TLS auf dem ESP32 zu viel RAM benötigt und instabil sein kann. Benachrichtigungen können stabiler über diesen Weg umgesetzt werden:

```text
ESP32 → MQTT → Home Assistant Automation → Telegram
```

## Funktionen

- Webdashboard für lokale Bedienung
- Feuchtigkeitssensor pro Kanal
- Pumpe/Relais/MOSFET pro Kanal
- manuelles Starten/Stoppen
- GPIO-Test
- Automatik EIN/AUS pro Kanal
- Trocken-/Nass-ADC-Werte im Webinterface einstellbar
- Grenzwert in Prozent einstellbar
- maximale Pumpenlaufzeit
- Cooldown pro Kanal
- Status pro Kanal
- MQTT-Publishing
- Home-Assistant-MQTT-Discovery
- OTA-Update über GitHub-RAW-Dateien
- Windows-/Python-Installer mit `mpremote`

## Standard-Hardware

| Funktion | Standard |
|---|---:|
| ESP32 | ESP32 WROOM |
| Sensor Kanal 1 | GPIO34 |
| Pumpe Kanal 1 | GPIO27 |
| Sensor-Typ | analoger Bodenfeuchtigkeitssensor |
| Pumpenversorgung | externes 5V-Netzteil empfohlen |

Wichtig:

- GPIO34 ist nur Eingang.
- Die Pumpe nicht direkt vom ESP32 versorgen.
- ESP32-GND und externes Netzteil-GND verbinden.
- Bei DC-Pumpen eine Freilaufdiode direkt parallel zur Pumpe verwenden.
- Bei Relaismodulen prüfen, ob sie `active-low` sind.

## Projektstruktur

```text
.
├── src/
│   ├── boot.py
│   ├── main.py
│   ├── config.py
│   ├── config.json
│   ├── hardware.py
│   ├── irrigation.py
│   ├── mqtt_client.py
│   ├── ota.py
│   ├── setup_portal.py
│   ├── storage.py
│   ├── webserver.py
│   ├── wifi_manager.py
│   └── index.html
│
├── installer/
│   ├── install.py
│   └── requirements.txt
│
├── ota/
│   ├── version.json
│   └── manifest.json
│
├── docs/
│   ├── INSTALLATION.md
│   ├── HARDWARE.md
│   ├── MQTT_HOME_ASSISTANT.md
│   └── OTA.md
│
├── config.example.json
├── .gitignore
└── README.md
```

## Installation

### 1. ZIP/Repository herunterladen

```powershell
git clone https://github.com/JannWdl/ESP32-Bodenfeuchtigkeit-HA.git
cd ESP32-Bodenfeuchtigkeit-HA
```

Oder ZIP herunterladen und entpacken.

### 2. ESP32 verbinden

COM-Port prüfen, zum Beispiel im Geräte-Manager oder per:

```powershell
python -m serial.tools.list_ports
```

### 3. Projekt hochladen

Ohne Flashen der Firmware:

```powershell
python installer\install.py COM8 --skip-flash
```

Kompletter Reset der Konfiguration:

```powershell
python installer\install.py COM8 --skip-flash --reset-config
```

MicroPython neu flashen:

```powershell
python installer\install.py COM8 --flash --erase --firmware esp32-micropython.bin
```

## Ersteinrichtung

Wenn keine WLAN-Daten vorhanden sind oder WLAN fehlschlägt, startet der ESP32 einen Setup-AP:

```text
SSID: Irrigation-Setup
Passwort: keins
URL: http://192.168.4.1
```

Dort WLAN eintragen, speichern und ESP32 neu starten.

Danach öffnest du im Heimnetz:

```text
http://<ESP32-IP>/
```

Beispiel:

```text
http://192.168.178.65/
```

## MQTT / Home Assistant einrichten

Im Webinterface im Reiter **MQTT**:

| Feld | Beispiel |
|---|---|
| MQTT aktivieren | an |
| Home Assistant Discovery | an |
| Broker Host | IP von Home Assistant |
| Port | 1883 |
| Benutzername | dein MQTT-Benutzer |
| Passwort | dein MQTT-Passwort |
| Base Topic | smart_irrigation |

Danach:

1. **MQTT speichern**
2. **MQTT testen**
3. **Jetzt Werte senden**
4. Optional: **HA Discovery senden**

### Topics

```text
smart_irrigation/status
smart_irrigation/channel/0/moisture
smart_irrigation/channel/0/raw_adc
smart_irrigation/channel/0/pump/state
smart_irrigation/channel/0/auto/state
smart_irrigation/channel/0/cooldown_remaining
```

## Home Assistant Benachrichtigung über Telegram

Empfohlener Ablauf:

```text
ESP32 → MQTT → Home Assistant Automation → Telegram
```

Beispiel-Automation-Idee:

```yaml
alias: Smart Irrigation Pumpe gestartet
trigger:
  - platform: mqtt
    topic: smart_irrigation/channel/0/pump/state
    payload: "ON"
action:
  - service: notify.telegram
    data:
      message: "Smart Irrigation: Pumpe Kanal 1 gestartet."
```

## OTA über GitHub

Die OTA-Funktion lädt Dateien über GitHub Raw:

```text
https://raw.githubusercontent.com/JannWdl/ESP32-Bodenfeuchtigkeit-HA/main/...
```

Dafür müssen diese Dateien im Repository vorhanden sein:

```text
ota/version.json
ota/manifest.json
src/*.py
src/index.html
```

Im Webinterface kann OTA geprüft werden. Das eigentliche Update sollte nur gestartet werden, wenn Stromversorgung und WLAN stabil sind.

## Aktuelle Version

```text
3.6.0
```

## Hinweise

`WEB_TIMEOUT_IGNORED` im seriellen Log ist meist nur ein Browser-/Socket-Timeout und nicht kritisch.

Wenn die Pumpe den ESP32 resetet oder WLAN ausfällt:

- Pumpe separat versorgen
- gemeinsame Masse prüfen
- Freilaufdiode direkt an der Pumpe prüfen
- Relais/MOSFET-Modul prüfen
- Kabel kürzer führen
- ggf. MOSFET statt Relais verwenden

## Lizenz

Optional ergänzen, z. B. MIT License.
