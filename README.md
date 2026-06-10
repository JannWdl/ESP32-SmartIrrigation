# ESP32 Smart Irrigation

ESP32/MicroPython-Bewässerungssteuerung mit Webinterface, MQTT, Home Assistant MQTT Discovery und Telegram-Steuerung über Home Assistant.

> Version: **v3.9.0**  
> Ziel: stabiler ESP32 ohne Telegram/HTTPS/TLS direkt auf dem Mikrocontroller.

## Kurzüberblick

Der ESP32 liest die Bodenfeuchtigkeit, steuert eine Pumpe/Relais und kommuniziert per MQTT mit Home Assistant. Telegram läuft bewusst **nicht** auf dem ESP32. Home Assistant empfängt Telegram-Befehle und sendet daraus einfache MQTT-Kommandos an den ESP.

```text
Telegram App
  ↓
Home Assistant Telegram Bot
  ↓
Home Assistant Automation / Scripts
  ↓ MQTT
ESP32 Smart Irrigation
  ↓
Pumpe / Relais / Sensor
```

## Hardware

Aktuelle Standard-Pins:

```text
Pumpe / Relais: GPIO27
Bodenfeuchtigkeit ADC: GPIO34
```

Wichtige Regeln:

- ESP32 versorgt die Pumpe **niemals direkt**.
- Pumpe nicht über Breadboard-Stromschienen laufen lassen.
- Alle GNDs müssen gemeinsam verbunden sein.
- Buck Converter vor Anschluss auf **5.0 V** einstellen.
- Bei DC-Pumpe: 1N4007-Freilaufdiode parallel zur Pumpe, Streifen an Pumpen-Plus.
- 470–1000 µF Elko nahe ESP32 5V/GND ist empfohlen.

## Installation auf ESP32

Normales Update ohne erneutes Flashen:

```powershell
python install.py COM8 --skip-flash
```

Interaktiv:

```powershell
python install.py
```

Details: [README_INSTALL.md](README_INSTALL.md)

## Home Assistant

Kopiere das Paket:

```text
aktuell/home_assistant/packages/esp_smart_irrigation.yaml
```

nach:

```text
/config/packages/esp_smart_irrigation.yaml
```

In `/config/configuration.yaml` aktivieren:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Dann Home Assistant neu starten.

Mehr dazu: [docs/HOME_ASSISTANT_SETUP.md](docs/HOME_ASSISTANT_SETUP.md)

## Telegram

Telegram wird über Home Assistant gesteuert. Der ESP32 enthält keinen Telegram-Token und macht kein HTTPS/TLS.

Befehle:

```text
/status
/pump5
/pump10
/stop
/auto_on
/auto_off
/discovery
```

Tutorial inklusive BotFather-Autovervollständigung: [docs/TELEGRAM_TUTORIAL.md](docs/TELEGRAM_TUTORIAL.md)

## MQTT Topics

```text
smart_irrigation/channel/0/command/pump        ON | OFF | RUN:5 | RUN:10
smart_irrigation/channel/0/command/auto        ON | OFF
smart_irrigation/system/command/stop           STOP
smart_irrigation/system/command/discovery      DISCOVERY
smart_irrigation/system/command/mqtt_interval  5..3600
```

## MQTT-Updateintervall

Einstellbar über:

1. ESP-Webinterface → MQTT → MQTT Update alle X Sekunden
2. Home Assistant Number-Entity `number.smart_irrigation_mqtt_updateintervall`
3. MQTT Topic `smart_irrigation/system/command/mqtt_interval`, z. B. Payload `60`

Empfehlung:

```text
30 Sekunden beim Testen
60–120 Sekunden im normalen Betrieb
```

## Release Notes

Siehe [RELEASE_NOTES.md](RELEASE_NOTES.md).
