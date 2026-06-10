# Home Assistant Dateien

## Empfohlener Weg: Package

Kopiere:

```text
home_assistant/packages/esp_smart_irrigation.yaml
```

nach:

```text
/config/packages/esp_smart_irrigation.yaml
```

In `/config/configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Dann Home Assistant neu starten.

## Telegram

Telegram läuft nur auf Home Assistant, nicht auf dem ESP32.

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

Wichtig für Home Assistant 2026.x:

- In `telegram_bot.send_message` wird `chat_id` verwendet.
- `target` wird nicht mehr verwendet.
- Das alte `notify: - platform: telegram` Beispiel wurde entfernt.

## Telegram Autovervollständigung

In BotFather `/setcommands` verwenden und einfügen:

```text
status - Status der Bewässerung anzeigen
pump5 - Pumpe 5 Sekunden starten
pump10 - Pumpe 10 Sekunden starten
stop - Not-Aus senden
auto_on - Automatik einschalten
auto_off - Automatik ausschalten
discovery - MQTT Discovery neu senden
```

## MQTT-Updateintervall

Ändern über:

1. ESP-Webinterface
2. Home Assistant Number `number.smart_irrigation_mqtt_updateintervall`
3. MQTT direkt: `smart_irrigation/system/command/mqtt_interval`, Payload z. B. `60`

Weitere Details siehe `/docs` im Repository.
