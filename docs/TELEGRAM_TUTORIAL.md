# Telegram Tutorial für ESP Smart Irrigation

Telegram läuft ausschließlich in Home Assistant. Der ESP32 bekommt keine Telegram-Token und macht kein HTTPS/TLS.

## 1. Bot mit BotFather erstellen

1. In Telegram `@BotFather` öffnen.
2. `/newbot` senden.
3. Namen vergeben, z. B. `Smart Irrigation`.
4. Usernamen vergeben, muss auf `bot` enden, z. B. `smart_irrigation_jann_bot`.
5. BotFather gibt dir einen Token.

Den Token niemals in GitHub pushen.

## 2. Chat-ID herausfinden

1. Deinem neuen Bot `/start` schreiben.
2. Deine Chat-ID ermitteln, z. B. über einen ID-Bot oder über die Home-Assistant-Events.
3. In `/config/secrets.yaml` eintragen:

```yaml
telegram_bot_token: "DEIN_TELEGRAM_BOT_TOKEN"
telegram_chat_id: 123456789
```

## 3. Telegram Bot in Home Assistant aktivieren

In `/config/configuration.yaml`:

```yaml
telegram_bot:
  - platform: polling
    api_key: !secret telegram_bot_token
    allowed_chat_ids:
      - !secret telegram_chat_id
```

Wichtig: Kein altes Telegram-Notify mehr eintragen:

```yaml
# NICHT mehr verwenden:
# notify:
#   - platform: telegram
#     name: telegram_jann
#     chat_id: !secret telegram_chat_id
```

## 4. Home Assistant Paket installieren

Kopiere:

```text
aktuell/home_assistant/packages/esp_smart_irrigation.yaml
```

nach:

```text
/config/packages/esp_smart_irrigation.yaml
```

Dann Home Assistant neu starten.

## 5. Telegram-Befehle

```text
/status      Status anzeigen
/pump5       Pumpe 5 Sekunden starten
/pump10      Pumpe 10 Sekunden starten
/stop        Not-Aus senden
/auto_on     Automatik einschalten
/auto_off    Automatik ausschalten
/discovery   Home-Assistant MQTT Discovery neu senden
```

## 6. Autovervollständigung / Befehlsmenü in Telegram aktivieren

Damit Telegram die Befehle vorschlägt, wenn du `/` eintippst:

1. `@BotFather` öffnen.
2. `/setcommands` senden.
3. Deinen Bot auswählen.
4. Diesen Block einfügen:

```text
status - Status der Bewässerung anzeigen
pump5 - Pumpe 5 Sekunden starten
pump10 - Pumpe 10 Sekunden starten
stop - Not-Aus senden
auto_on - Automatik einschalten
auto_off - Automatik ausschalten
discovery - MQTT Discovery neu senden
```

Danach zeigt Telegram die Befehle im Slash-Menü an.

Hinweis: BotFather erwartet beim Eintragen meistens `status - Beschreibung`, also ohne `/` am Anfang. Im Chat verwendest du die Befehle weiterhin mit `/status`.

## 7. Test

Schreibe deinem Bot:

```text
/status
```

Erwartete Antwort:

```text
🌱 Smart Irrigation Status

Bodenfeuchtigkeit: 71 %
ADC: 2075

Pumpe: AUS
Automatik: AN

Cooldown: 1888 s
MQTT Update: 30 s
```

Dann:

```text
/pump5
```

Die Pumpe sollte für 5 Sekunden laufen und Home Assistant sollte antworten.

## 8. Häufige Fehler

### Telegram antwortet nicht

Prüfen:

- Bot einmal manuell mit `/start` angeschrieben?
- Chat-ID korrekt?
- `telegram_bot:` in `configuration.yaml` aktiv?
- Home Assistant neu gestartet?
- Automation `ESP Smart Irrigation - Telegram Commands` aktiv?

### Warnung: target wird entfernt

In `telegram_bot.send_message` darf nicht mehr stehen:

```yaml
target: 123456789
```

Richtig ist:

```yaml
chat_id: 123456789
```

In dieser Version ist das Paket bereits darauf angepasst.

### Status zeigt unknown

Dann passen die Entity-IDs nicht. Suche unter:

```text
Entwicklerwerkzeuge → Zustände → smart_irrigation
```

und passe die Entity-IDs im Paket an.
