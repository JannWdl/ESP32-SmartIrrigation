# V4 mit Home Assistant verbinden

[Projekt](../README.md) · [Dokumentation](README.md)

V4 verwendet Home Assistant MQTT Discovery. Die Bewässerung und alle Mengenlimits laufen weiterhin auf dem ESP32.

## Einrichtung

1. Einen erreichbaren MQTT-Broker bereitstellen und die MQTT-Integration in Home Assistant mit diesem Broker verbinden.
2. In der Geräteoberfläche MQTT aktivieren: Brokeradresse, Port und bei Bedarf Benutzername und Passwort eintragen. Beide Systeme müssen denselben Broker verwenden.
3. Für ein einzelnes Gerät kann das Standard-Basistopic `smart_irrigation_v4` bleiben. Für mehrere Geräte je ein eigenes Topic wählen.
4. Speichern und den Verbindungsstatus am Gerät prüfen. Unter der MQTT-Integration erscheint das Gerät mit seinem eingestellten Namen.

Eine zusätzliche HACS-Integration oder das alte V3-Paket ist für V4 nicht erforderlich. Die historischen V3-Beispiele verwenden andere Topics und Befehle.

## Was automatisch erscheint

| Bereich | Entitäten |
|---|---|
| Tank | Füllstand in Prozent, geschätzte Liter, „Wasser nachfüllen oder Sensor prüfen“. |
| Steuerung | „Bewässerung gesperrt“, „Alles stoppen“, „Automatik freigeben“. |
| Je Pflanzenkanal | Bodenfeuchtigkeit, Status, Wasserportion und Automatikschalter. |

Die Portionstaste fordert die am Gerät konfigurierte Menge an. Die Steuerung kann sie bei einer aktiven Sperre ablehnen. „Alles stoppen“ sperrt die Automatik bis zur ausdrücklichen Freigabe.

## Meldungen

Die [Beispielautomation](../rebuild/home_assistant/notifications.yaml) meldet Fehlerereignisse über einen mobilen Notify-Dienst. Vor der Verwendung Topic und `notify.mobile_app_DEIN_HANDY` anpassen. Telegram kann ebenfalls über Home Assistant ergänzt werden.

## Topics zur Diagnose

Mit dem Standard-Basistopic:

| Topic | Inhalt |
|---|---|
| `smart_irrigation_v4/availability` | `online` / `offline`. |
| `smart_irrigation_v4/state` | JSON-Status für Tank und Kanäle. |
| `smart_irrigation_v4/event` | Ereignisse und Fehler. |
| `smart_irrigation_v4/result` | Antwort auf einen Befehl, einschließlich Ablehnungsgrund. |
| `smart_irrigation_v4/command` | JSON-Steuerbefehle; bevorzugt die entdeckten Entitäten bedienen. |

Steuerbefehle werden nur mit QoS 0 und ohne Retain ausgeführt. Retained-Befehle werden bewusst verworfen, damit alte Bewässerungsanforderungen nach einer Wiederverbindung nicht erneut starten.

## Wenn etwas fehlt

- Alle Entitäten gleichzeitig „Nicht verfügbar“: MQTT-Verbindung und Verfügbarkeit des Geräts prüfen.
- Taste gedrückt, aber kein Wasser: Pflanzenstatus, Tankstatus und Ereignisverlauf am Gerät ansehen; eine aktive Sperre bleibt auch über HA wirksam.
- Gerät fehlt nach Neustart: Broker und Discovery prüfen. V4 veröffentlicht die Discovery-Daten beim Verbinden und nach dem HA-Online-Signal erneut.
- Doppelte Einträge aus V3: Erst die alten Geräte und Automationen zuordnen; anschließend gezielt die überholten Einträge entfernen. Keine pauschale Löschung fremder MQTT-Discovery-Topics.
