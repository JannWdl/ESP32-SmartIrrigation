# Hardware vor Freigabe prüfen

Bekannt: zwei Kanäle, kapazitive analoge Sensoren, 5-V-Pumpen, Relais, HC-SR04,
ein gemeinsamer Wasserbehälter. Board laut Produktbild: diymore ESP32-NodeMCU / ESP-WROOM-32
mit USB-C und CH340. Vorbelegung Sensoren 34/35, Relais 27/26, Trigger 18, Echo 19.
Unbekannt: LOW/HIGH-Relaislogik,
Behälterform/-maße und Pumpenfördermengen. **Keine automatische Übernahme alter GPIOs.**

- HC-SR04 benötigt laut Datenblatt 5 V. Echo nicht direkt mit einem ESP32-Eingang verbinden:
  Pegelwandlung oder geeigneten Spannungsteiler auf 3,3 V einsetzen. Sensor/ESP gemeinsame Masse.
  Das HC-SR04-Modul ist nicht wasserdicht: trocken und oberhalb des Wassers montieren.
  Datenblatt: https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf
- Pumpe aus einer passend dimensionierten 5-V-Versorgung über Relaiskontakte versorgen,
  nicht aus einem GPIO. Bei DC-Pumpen Schutzbeschaltung und Entstörung berücksichtigen.
- Relaislogik ohne angeschlossene Pumpenversorgung messen und bestätigen.
  Externer Pull-up/Pull-down muss das Relais auch vor Firmwarestart und beim Reset ausschalten.
- Die Software bietet eine konservative GPIO-Auswahl für ESP32/WROOM und ESP32-S3.
  Die tatsächliche Boardbeschaltung hat Vorrang, insbesondere belegte PSRAM/Flash-/USB-Pins.
- ADC-Kalibrierung wird auf 12-Bit-Rohwerten (0..4095) vorgenommen. Werte an den Versorgungsschienen
  werden als Fehler behandelt. Ein schwebender/abgezogener Analogeingang lässt sich nicht immer
  zuverlässig softwareseitig erkennen; bei Bedarf zusätzliche elektrische Sensorüberwachung vorsehen.
- Tankkalibrierung: Abstand voll < Abstand Wiederfreigabe < Abstand Reserve <= Abstand leer.
  Reserve über der Ansaugöffnung setzen. Unregelmäßige Behälter mit mehreren bekannten Literständen
  kalibrieren. Prozentanzeige basiert auf Füllhöhe; Literanzeige auf den Messpunkten.
- Erst Messbecherläufe, dann einzelne kurze Bewässerungen unter Beobachtung testen.
- Vor Upload/USB-Installation Pumpenversorgung physisch trennen. Die Bestätigung im Installer
  ist eine Angabe des Bedieners und keine elektrisch gemessene Trennung.

MicroPython-Referenzen:
https://docs.micropython.org/en/latest/library/machine.html
https://docs.micropython.org/en/latest/library/asyncio.html
