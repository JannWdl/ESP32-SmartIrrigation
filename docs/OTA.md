# OTA über GitHub

OTA nutzt GitHub Raw-Dateien.

Benötigt:

```text
ota/version.json
ota/manifest.json
src/*.py
src/index.html
```

Die Manifest-Datei enthält die Dateien, die auf den ESP32 geladen werden sollen.

`config.json` sollte per OTA nicht überschrieben werden, damit WLAN/MQTT-Einstellungen erhalten bleiben.
