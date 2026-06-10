# Telegram ohne ESP32-Direct-Verbindung

In dieser Version läuft Telegram **nicht mehr auf dem ESP32**. Der ESP32 macht nur noch:

- WLAN
- Webinterface
- MQTT Statuswerte
- MQTT Kommandos
- Pumpensteuerung
- Automatik

Telegram läuft über Home Assistant. Vorteil: Der ESP32 muss kein HTTPS/TLS und kein Telegram-Polling machen. Das spart RAM und verhindert Instabilität.

## MQTT Updateintervall einstellen

Im Webinterface:

1. Tab **MQTT** öffnen
2. Feld **MQTT Update alle X Sekunden** einstellen
3. **MQTT speichern** klicken

Minimum ist 5 Sekunden. Praktisch empfehlenswert: 30 bis 120 Sekunden.

## MQTT-Kommandos

Base Topic standardmäßig:

```text
smart_irrigation
```

Wichtige Topics:

```text
smart_irrigation/channel/0/command/pump
smart_irrigation/channel/0/command/auto
smart_irrigation/channel/0/command/run
smart_irrigation/system/command/stop
smart_irrigation/system/command/discovery
```

Payloads:

```text
Pumpe: ON, OFF, RUN:5, RUN:10
Auto: ON, OFF
Run: 5, 10, 15 ...
Stop: STOP
Discovery: DISCOVERY
```

## Telegram in Home Assistant

Die fertige Automation liegt hier:

```text
home_assistant/telegram_mqtt_proxy.yaml
```

Diese Automation nimmt Telegram-Befehle entgegen und sendet passende MQTT-Kommandos an den ESP32.

Befehle:

```text
/status
/pump5
/pump10
/stop
/auto_on
/auto_off
```

## Wichtig

Alte Dateien wie `telegram_bot.py` oder `telegram_notify.py` werden nicht mehr von `main.py` geladen. Telegram-Token und Chat-ID gehören nicht mehr auf den ESP32.
