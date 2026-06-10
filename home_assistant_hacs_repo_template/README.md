# ESP Smart Irrigation - Home Assistant Custom Integration

Diese Vorlage ist für eine spätere HACS-Veröffentlichung gedacht.

Sie läuft **nur in Home Assistant**, nicht auf dem ESP32.
Die Integration stellt einfache Dienste bereit, die MQTT-Kommandos an den ESP32 senden.

## Installation manuell

Den Ordner kopieren nach:

```text
/config/custom_components/esp_smart_irrigation
```

Danach Home Assistant neu starten und die Integration über:

```text
Einstellungen → Geräte & Dienste → Integration hinzufügen → ESP Smart Irrigation
```

hinzufügen.

## Dienste

Domain:

```text
esp_smart_irrigation
```

Dienste:

```text
esp_smart_irrigation.pump_on
esp_smart_irrigation.pump_off
esp_smart_irrigation.pump_run
esp_smart_irrigation.auto_on
esp_smart_irrigation.auto_off
esp_smart_irrigation.emergency_stop
esp_smart_irrigation.rediscovery
```

## Beispiel Automation Telegram → MQTT

```yaml
action: esp_smart_irrigation.pump_run
data:
  seconds: 10
```

## HACS

Für HACS muss dieser Ordner der Root eines eigenen GitHub-Repos sein.
Die Struktur muss so bleiben:

```text
custom_components/esp_smart_irrigation/...
hacs.json
README.md
```
