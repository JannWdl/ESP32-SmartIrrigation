# Hinweis zum ESP32 Guru Meditation / IllegalInstruction

Wenn direkt nach dem Start ein Core-Panic kommt, ist das kein normaler Python-Traceback.
Diese Version reduziert deshalb Hintergrund-Netzwerkaktivität:

- MQTT verbindet nicht mehr sofort beim Boot
- MQTT publish ist gedrosselt
- Pumpen werden bei Fehlern ausgeschaltet
- Setup und Integrationen sind über die Weboberfläche konfigurierbar

Falls es weiterhin crasht:
- andere MicroPython Firmware testen
- ohne OTA-Partition-Firmware testen
- ESP32 komplett löschen und frisch flashen
- Pumpe/Relais testweise komplett abziehen
