# Home Assistant Setup

## 1. MQTT einrichten

In Home Assistant:

```text
Einstellungen → Geräte & Dienste → Integration hinzufügen → MQTT
```

Bei Mosquitto Add-on meistens:

```text
Host: core-mosquitto
Port: 1883
```

Der ESP32 muss dieselben MQTT-Zugangsdaten verwenden.

## 2. MQTT Discovery prüfen

Im ESP-Webinterface:

```text
MQTT aktivieren
Base Topic: smart_irrigation
HA Discovery senden
```

Oder per Home Assistant senden:

```yaml
service: mqtt.publish
data:
  topic: smart_irrigation/system/command/discovery
  payload: "DISCOVERY"
```

Danach sollten unter MQTT-Geräte die Entities erscheinen.

## 3. Home-Assistant-Paket installieren

Datei kopieren:

```text
aktuell/home_assistant/packages/esp_smart_irrigation.yaml
```

nach:

```text
/config/packages/esp_smart_irrigation.yaml
```

In `/config/configuration.yaml` ergänzen:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Wenn bereits ein `homeassistant:` Block existiert, nur die `packages`-Zeile darunter ergänzen.

Danach:

```text
Entwicklerwerkzeuge → YAML → Konfiguration prüfen
Einstellungen → System → Neustarten
```

## 4. Erwartete Entity-IDs

Die aktuelle Discovery erzeugt normalerweise:

```text
sensor.smart_irrigation_kanal_1_feuchtigkeit
sensor.smart_irrigation_kanal_1_adc
sensor.smart_irrigation_kanal_1_cooldown
binary_sensor.smart_irrigation_kanal_1_pumpe
binary_sensor.smart_irrigation_kanal_1_automatik
switch.smart_irrigation_kanal_1_pumpe_manuell
switch.smart_irrigation_kanal_1_auto_steuerung
number.smart_irrigation_mqtt_updateintervall
button.smart_irrigation_kanal_1_pumpe_5s
button.smart_irrigation_kanal_1_pumpe_10s
button.smart_irrigation_not_aus
button.smart_irrigation_ha_discovery_neu_senden
```

Wenn deine Namen abweichen, in Home Assistant unter `Entwicklerwerkzeuge → Zustände` nach `smart_irrigation` suchen und die YAML entsprechend anpassen.

## 5. MQTT direkt testen

Pumpe 5 Sekunden:

```yaml
service: mqtt.publish
data:
  topic: smart_irrigation/channel/0/command/pump
  payload: "RUN:5"
```

Not-Aus:

```yaml
service: mqtt.publish
data:
  topic: smart_irrigation/system/command/stop
  payload: "STOP"
```

MQTT Updateintervall 60 Sekunden:

```yaml
service: mqtt.publish
data:
  topic: smart_irrigation/system/command/mqtt_interval
  payload: "60"
```

## 6. Doppelte Automationen vermeiden

Wenn du vorher manuell eine Telegram-Automation erstellt hast, kann es zwei Einträge geben:

```text
ESP Smart Irrigation - Telegram Commands
ESP Smart Irrigation - Telegram Commands
```

Nur eine darf aktiv sein. Die alte/deaktivierte löschen oder ausschalten.
