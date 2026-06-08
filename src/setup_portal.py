"""
setup_portal.py v2.9
Sichtbarer Fallback-AP:
- STA wird komplett deaktiviert
- AP ist standardmäßig OFFEN, kein WPA
- Kanal 1
- kurzer SSID-Name: Irrigation-Setup
"""
import network
import socket
import time
import gc
from config import get_config, save_config

HTML = """HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation Setup</title>
<style>
body{font-family:Arial;background:#07130f;color:#eefcf4;padding:20px;margin:0}
.card{max-width:560px;margin:30px auto;background:#10231b;padding:24px;border-radius:24px;border:1px solid #ffffff22}
input,button{width:100%;padding:14px;margin:8px 0;border-radius:14px;border:0;font-size:16px}
input{background:#0005;color:#eefcf4;border:1px solid #ffffff22}
button{background:#16a35a;color:white;font-weight:bold}
p{color:#9db5a8}
</style></head><body><div class="card">
<h1>🌱 Smart Irrigation Setup</h1>
<p>Verbinde dich mit dem Setup-WLAN und trage dein Heim-WLAN ein.</p>
<form method="POST" action="/save">
<input name="ssid" placeholder="WLAN SSID" autocomplete="off">
<input name="password" type="password" placeholder="WLAN Passwort">
<button type="submit">Speichern</button>
</form>
<p>Setup-AP: Irrigation-Setup<br>Passwort: keins/offen<br>Adresse: http://192.168.4.1</p>
</div></body></html>
"""

SAVED = """HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

<!doctype html><html><body style="font-family:Arial;background:#07130f;color:#eefcf4;padding:20px">
<h1>✅ WLAN gespeichert</h1><p>ESP32 jetzt neu starten.</p></body></html>
"""

def _hex(c):
    if "0" <= c <= "9":
        return ord(c) - 48
    c = c.lower()
    if "a" <= c <= "f":
        return ord(c) - 87
    return 0

def url_decode(s):
    s = s.replace("+", " ")
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            out.append(_hex(s[i+1]) * 16 + _hex(s[i+2]))
            i += 3
        else:
            out.extend(s[i].encode())
            i += 1
    try:
        return out.decode("utf-8")
    except Exception:
        return str(out)

def parse_form(body):
    result = {}
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            result[url_decode(k)] = url_decode(v)
    return result

def recv_request(conn):
    data = b""
    while b"\r\n\r\n" not in data and len(data) < 4096:
        chunk = conn.recv(512)
        if not chunk:
            break
        data += chunk
    if b"\r\n\r\n" in data:
        header, body = data.split(b"\r\n\r\n", 1)
    else:
        header, body = data, b""
    header_text = header.decode("utf-8", "ignore")
    content_length = 0
    for line in header_text.split("\r\n"):
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except Exception:
                pass
    while len(body) < content_length:
        try:
            chunk = conn.recv(content_length - len(body))
            if not chunk:
                break
            body += chunk
        except Exception:
            break
    first = header_text.split("\r\n", 1)[0] if header_text else ""
    return first, body.decode("utf-8", "ignore")

def start_setup_portal(reason=""):
    print("Starte Setup-AP...", reason)

    cfg = get_config()
    wifi = cfg.get("wifi", {})
    ssid = wifi.get("setup_ap_ssid", "Irrigation-Setup")
    password = wifi.get("setup_ap_password", "")
    open_ap = bool(wifi.get("setup_ap_open", True))
    channel = int(wifi.get("setup_ap_channel", 1))

    # Ganz wichtig: STA aus, damit AP sicher sichtbar wird.
    try:
        sta = network.WLAN(network.STA_IF)
        try:
            sta.disconnect()
        except Exception:
            pass
        sta.active(False)
        time.sleep(1)
    except Exception as exc:
        print("STA disable Fehler:", exc)

    ap = network.WLAN(network.AP_IF)
    try:
        ap.active(False)
        time.sleep(1)
    except Exception:
        pass

    gc.collect()

    # OFFENER AP ist am kompatibelsten und wird am zuverlässigsten angezeigt.
    ap.active(True)
    time.sleep(0.5)

    try:
        if open_ap:
            ap.config(essid=ssid, channel=channel, hidden=False, max_clients=4)
        else:
            ap.config(essid=ssid, password=password or "12345678", authmode=network.AUTH_WPA_WPA2_PSK, channel=channel, hidden=False, max_clients=4)
    except TypeError:
        # Einige Builds kennen hidden/max_clients nicht.
        if open_ap:
            ap.config(essid=ssid, channel=channel)
        else:
            ap.config(essid=ssid, password=password or "12345678", authmode=network.AUTH_WPA_WPA2_PSK, channel=channel)

    time.sleep(2)

    try:
        print("Setup-AP aktiv:", ap.active(), ap.ifconfig())
        print("Setup-AP config:", ap.config("essid"))
    except Exception as exc:
        print("AP config print Fehler:", exc)

    print("Setup-AP:", ssid, "/ offen" if open_ap else "/ " + (password or "12345678"))
    print("Öffne http://192.168.4.1")

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80))
    s.listen(1)

    while True:
        conn, addr = s.accept()
        try:
            first, body = recv_request(conn)
            if first.startswith("POST /save"):
                data = parse_form(body)
                home_ssid = data.get("ssid", "").strip()
                home_password = data.get("password", "")
                cfg = get_config()
                cfg["wifi"]["ssid"] = home_ssid
                cfg["wifi"]["password"] = home_password
                cfg["wifi"]["fallback_ap_on_fail"] = True
                cfg["system"]["setup_done"] = False
                save_config(cfg)
                print("WLAN gespeichert. SSID:", home_ssid)
                conn.send(SAVED)
            else:
                conn.send(HTML)
        except Exception as exc:
            print("Setup Portal Fehler:", exc)
            try:
                conn.send("HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\nFehler")
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
            time.sleep_ms(100)
