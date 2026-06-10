# Release Notes v3.9.0

## Schwerpunkt

Diese Version macht das Projekt GitHub-fertig für den aktuellen Stand mit Home Assistant und Telegram:

- Telegram läuft weiterhin nicht auf dem ESP32.
- Home Assistant übernimmt Telegram-Befehle.
- Veralteter Telegram-Parameter `target` wurde durch `chat_id` ersetzt.
- Status-Meldung nutzt die korrekten MQTT-Discovery-Entity-IDs.
- Doku, Release Notes und Tutorials wurden ergänzt.

## Neu

### Home Assistant Paket aktualisiert

Datei:

```text
aktuell/home_assistant/packages/esp_smart_irrigation.yaml
```

Änderungen:

- `/status` funktioniert mit den aktuellen Entity-IDs.
- Telegram-Antworten nutzen `chat_id` statt `target`.
- MQTT-Updateintervall ist über HA steuerbar.
- Scripts für Pumpe, Auto, Stop, Discovery und MQTT-Intervalle enthalten.

### Telegram Tutorial

Neu:

```text
docs/TELEGRAM_TUTORIAL.md
```

Enthält:

- BotFather-Einrichtung
- Home Assistant Telegram Bot Setup
- Befehle
- Autovervollständigung per `/setcommands`
- Fehlerbehebung

### Home Assistant Tutorial

Neu:

```text
docs/HOME_ASSISTANT_SETUP.md
```

Enthält:

- MQTT Setup
- Package Installation
- erwartete Entity-IDs
- MQTT-Direkttests
- Hinweise zu doppelten Automationen

### Architektur-Doku

Neu:

```text
docs/ARCHITECTURE.md
```

Erklärt, warum Telegram nicht auf dem ESP32 läuft und warum MQTT die stabile Lösung ist.

## Geändert

- `telegram_bot.py`, `telegram_notify.py` und `mqtt_ha.py` wurden aus dem ESP-Projektordner entfernt, damit keine veralteten Telegram-Direct-Dateien mehr im Projekt liegen.
- `version.json` auf v3.9.0 aktualisiert.
- `README.md` für GitHub ergänzt.
- `telegram_bot_example.yaml` verwendet kein altes `notify: platform: telegram` mehr.

## MQTT Commands

```text
smart_irrigation/channel/0/command/pump        ON | OFF | RUN:5 | RUN:10
smart_irrigation/channel/0/command/auto        ON | OFF
smart_irrigation/system/command/stop           STOP
smart_irrigation/system/command/discovery      DISCOVERY
smart_irrigation/system/command/mqtt_interval  5..3600
```

## Update-Hinweise

1. ESP32 aktualisieren:

```powershell
python install.py COM8 --skip-flash
```

2. Home Assistant Paket neu kopieren:

```text
aktuell/home_assistant/packages/esp_smart_irrigation.yaml
→ /config/packages/esp_smart_irrigation.yaml
```

3. Alte doppelte Telegram-Automationen deaktivieren oder löschen.
4. Home Assistant neu starten.
5. Telegram mit `/status` testen.

## Bekannte Hinweise

- Wenn `/status` `unknown` zeigt, weichen deine Entity-IDs ab. Suche in `Entwicklerwerkzeuge → Zustände` nach `smart_irrigation`.
- Wenn HA eine Telegram-Migration meldet, suche nach `target:` in Automationen/Scripts. Bei `telegram_bot.send_message` muss daraus `chat_id:` werden.
