import time
import network
import gc

def _safe_reset_sta():
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.disconnect()
    except Exception:
        pass
    try:
        wlan.active(False)
        time.sleep(0.6)
    except Exception:
        pass
    gc.collect()
    wlan.active(True)
    time.sleep(0.4)
    return wlan

def connect_wifi(cfg, timeout=None):
    wifi_cfg = cfg.get("wifi", {})
    ssid = wifi_cfg.get("ssid", "")
    password = wifi_cfg.get("password", "")
    hostname = wifi_cfg.get("hostname", "smart-irrigation")
    attempts = int(wifi_cfg.get("connect_attempts", 3))
    if timeout is None:
        timeout = int(wifi_cfg.get("connect_timeout_seconds", 20))

    if not ssid:
        print("WLAN SSID fehlt.")
        return False, None

    try:
        network.hostname(hostname)
    except Exception:
        pass

    for attempt in range(1, attempts + 1):
        print("Verbinde WLAN: {} (Versuch {}/{})".format(ssid, attempt, attempts))
        try:
            wlan = _safe_reset_sta()
            wlan.connect(ssid, password)
            start = time.time()

            while time.time() - start < timeout:
                try:
                    if wlan.isconnected():
                        ip = wlan.ifconfig()[0]
                        print("WLAN verbunden:", ip)
                        return True, ip
                except Exception as exc:
                    print("WLAN Status Fehler:", exc)
                    break
                time.sleep(0.5)

            try:
                print("WLAN Status:", wlan.status())
            except Exception:
                pass

        except Exception as exc:
            print("WLAN Connect Fehler:", exc)

        time.sleep(1)
        gc.collect()

    print("WLAN Verbindung fehlgeschlagen.")
    return False, None

def reconnect_wifi(cfg, timeout=12):
    print("WLAN Recovery startet...")
    try:
        _safe_reset_sta()
    except Exception as exc:
        print("WLAN Recovery reset Fehler:", exc)
    return connect_wifi(cfg, timeout=timeout)

def status():
    try:
        wlan = network.WLAN(network.STA_IF)
        return {"connected": wlan.isconnected(), "ifconfig": wlan.ifconfig() if wlan.active() else None, "status": wlan.status()}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}
