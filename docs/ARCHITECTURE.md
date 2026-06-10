# Architektur

## Grundidee

Der ESP32 macht nur das, was lokal und sicher notwendig ist:

- Sensorwerte lesen
- Pumpe schalten
- automatische Bewässerung
- Webinterface
- MQTT senden/empfangen
- Home Assistant MQTT Discovery

Home Assistant übernimmt alles, was für einen ESP32 mit MicroPython unnötig schwer oder RAM-intensiv ist:

- Telegram Bot
- HTTPS/TLS
- Benachrichtigungen
- Dashboard
- Automationen

## Datenfluss

```text
ESP32 → MQTT Status → Home Assistant → Dashboard/Telegram
Telegram → Home Assistant → MQTT Command → ESP32
```

## Warum kein Telegram direkt auf dem ESP32?

Telegram benötigt HTTPS/TLS und Polling/Webhooks. Das ist auf MicroPython/ESP32 schnell instabil und verbraucht RAM. MQTT ist deutlich leichter, stabiler und besser debugbar.

## Sicherheitslogik bleibt auf dem ESP32

Auch wenn Home Assistant ausfällt, bleiben lokale Schutzfunktionen auf dem ESP32:

- Max-Laufzeit
- Cooldown
- Pumpenstopp
- Sensor-Plausibilität
- Auto-Bewässerung
