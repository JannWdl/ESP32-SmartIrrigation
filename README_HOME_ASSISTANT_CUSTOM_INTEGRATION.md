# ESP Smart Irrigation Custom Integration / HACS-Vorlage

Diese Vorlage ist für Home Assistant gedacht und sendet einfache MQTT-Kommandos an den ESP32.
Telegram bleibt die normale Home-Assistant-Telegram-Integration.

## Enthaltene Services

```text
esp_smart_irrigation.pump_on
esp_smart_irrigation.pump_off
esp_smart_irrigation.pump_run
esp_smart_irrigation.auto_on
esp_smart_irrigation.auto_off
esp_smart_irrigation.emergency_stop
esp_smart_irrigation.rediscovery
esp_smart_irrigation.set_mqtt_interval
```

Beispiel:

```yaml
service: esp_smart_irrigation.pump_run
data:
  channel: 0
  seconds: 10
```

MQTT-Intervall setzen:

```yaml
service: esp_smart_irrigation.set_mqtt_interval
data:
  seconds: 60
```

## HACS

Für HACS den Inhalt aus `home_assistant_hacs_repo_template/` in ein eigenes GitHub-Repo kopieren.
