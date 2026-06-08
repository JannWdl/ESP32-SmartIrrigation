# Hardware

## Standardpins

| Funktion | Pin |
|---|---:|
| Sensor Kanal 1 | GPIO34 |
| Pumpe Kanal 1 | GPIO27 |

## Wichtige Hinweise

- GPIO34 ist nur Eingang.
- Pumpe niemals direkt vom ESP32 versorgen.
- Externes Netzteil für die Pumpe verwenden.
- GND vom ESP32 und externem Netzteil verbinden.
- Bei DC-Pumpe eine Freilaufdiode nutzen.
- Bei Relaismodulen active-low prüfen.

## Freilaufdiode

Bei einer DC-Pumpe:

```text
Diode parallel zur Pumpe
Strichseite an Pumpen-Plus
andere Seite an Pumpen-Minus
```

Geeignet: z. B. 1N4007.
