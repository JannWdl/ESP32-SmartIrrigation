try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import gc
import time
from config import get_config, save_config
from hardware import HardwareManager
from wifi_manager import connect_wifi, reconnect_wifi
from setup_portal import start_setup_portal
from irrigation import IrrigationController
from mqtt_client import MQTTService
from ota import GitHubOTA
from webserver import WebServer

async def main():
    cfg = get_config()
    hwman = HardwareManager(cfg)
    hwman.all_pumps_off()

    ok, ip = connect_wifi(cfg)
    if not ok:
        print("WLAN fehlgeschlagen.")
        if cfg.get("wifi", {}).get("fallback_ap_on_fail", True):
            start_setup_portal("WLAN fehlgeschlagen")
            return
        print("Fallback-AP deaktiviert. Starte keinen normalen Webserver.")
        return
    telegram = None
    mqtt = MQTTService(cfg)
    irrigation = IrrigationController(cfg, hwman, telegram=None, mqtt=mqtt)
    ota = GitHubOTA(cfg, hardware_manager=hwman)
    web = WebServer(cfg, hwman, irrigation, telegram=None, mqtt=mqtt, ota=ota, ip=ip)
    web.start(80)

    asyncio.create_task(irrigation.auto_loop())
    print("Smart Irrigation läuft:", ip)

    loop_count = 0
    last_wifi_recovery = 0

    while True:
        try:
            # Nach Pumpenaktivität Netzwerk bewusst kurz entlasten.
            if irrigation.network_pause_active():
                await asyncio.sleep_ms(100)
            else:
                await web.poll()

            if loop_count % 100 == 0 and mqtt.enabled() and not irrigation.network_pause_active():
                if (not cfg.get("safety", {}).get("mqtt_publish_while_pump_running", False)) and irrigation.any_running():
                    pass
                else:
                    mqtt.publish_status(hwman.status(), irrigation.status())

        except OSError as exc:
            msg = str(exc)
            print("MAIN_OSERROR:", msg)
            try:
                hwman.all_pumps_off()
            except Exception:
                pass

            # Wichtig: Wifi Internal State Error automatisch reparieren.
            if "Wifi Internal State Error" in msg or "EIO" in msg:
                now = time.time()
                if cfg.get("safety", {}).get("auto_reconnect_wifi", True) and now - last_wifi_recovery > 10:
                    last_wifi_recovery = now
                    try:
                        web.close()
                    except Exception:
                        pass
                    ok, new_ip = reconnect_wifi(cfg, timeout=12)
                    if ok:
                        ip = new_ip
                        web.ip = ip
                        if cfg.get("safety", {}).get("restart_webserver_on_wifi_error", True):
                            web.start(80)
                        print("WLAN Recovery OK:", ip)
                    else:
                        print("WLAN Recovery fehlgeschlagen")
                await asyncio.sleep_ms(500)
            else:
                await asyncio.sleep_ms(250)

        except Exception as exc:
            msg = str(exc)
            print("MAIN_ERROR:", msg)
            try:
                hwman.all_pumps_off()
            except Exception:
                pass
            if "Wifi Internal State Error" in msg:
                try:
                    web.close()
                except Exception:
                    pass
                ok, new_ip = reconnect_wifi(cfg, timeout=12)
                if ok:
                    ip = new_ip
                    web.ip = ip
                    web.start(80)
                    print("WLAN Recovery OK:", ip)
            await asyncio.sleep_ms(250)

        loop_count += 1
        if loop_count > 1000000:
            loop_count = 0
        gc.collect()
        await asyncio.sleep_ms(20)

try:
    asyncio.run(main())
finally:
    try:
        asyncio.new_event_loop()
    except Exception:
        pass
