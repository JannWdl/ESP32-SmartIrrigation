# Installation

## Voraussetzungen

- Python 3
- ESP32 per USB
- `mpremote`
- optional `esptool`
- MicroPython auf dem ESP32

Der Installer installiert fehlende Python-Pakete automatisch nach.

## Upload ohne Firmware-Flash

```powershell
python installer\install.py COM8 --skip-flash
```

## Upload mit Konfigurations-Reset

```powershell
python installer\install.py COM8 --skip-flash --reset-config
```

## Firmware neu flashen

```powershell
python installer\install.py COM8 --flash --erase --firmware esp32-micropython.bin
```

## Wenn Upload hängt

- Seriellen Monitor schließen
- Thonny schließen
- Arduino IDE schließen
- ESP32 resetten
- COM-Port prüfen
- anderes USB-Datenkabel testen
