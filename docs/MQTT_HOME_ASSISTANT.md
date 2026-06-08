# MQTT und Home Assistant

## MQTT im Webinterface

Im Reiter MQTT eintragen:

```text
Host: IP von Home Assistant
Port: 1883
Benutzername: MQTT-Benutzer
Passwort: MQTT-Passwort
Base Topic: smart_irrigation
```

Danach:

1. MQTT speichern
2. MQTT testen
3. Jetzt Werte senden
4. HA Discovery senden

## Topics

```text
smart_irrigation/status
smart_irrigation/channel/0/moisture
smart_irrigation/channel/0/raw_adc
smart_irrigation/channel/0/pump/state
smart_irrigation/channel/0/auto/state
smart_irrigation/channel/0/cooldown_remaining
```

## Home Assistant prüfen

In Home Assistant:

```text
Entwicklerwerkzeuge → MQTT → Auf Topic hören
```

Topic:

```text
smart_irrigation/#
```

## Telegram über Home Assistant

Telegram direkt auf dem ESP32 wurde entfernt. Empfohlen:

```text
ESP32 → MQTT → Home Assistant Automation → Telegram
```
