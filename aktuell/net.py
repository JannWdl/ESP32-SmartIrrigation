import network
import time
import serial_log


def connect_or_ap(cfg):
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    wifi = cfg.get("wifi", {})
    if wifi.get("ssid"):
        serial_log.log("WLAN verbinde mit SSID: " + wifi.get("ssid", ""))
        sta.connect(wifi.get("ssid"), wifi.get("password", ""))
        for _ in range(30):
            if sta.isconnected():
                serial_log.log("WLAN verbunden: " + sta.ifconfig()[0])
                return "sta", sta.ifconfig()[0]
            time.sleep(1)
        serial_log.log("WLAN Verbindung fehlgeschlagen, starte Setup-AP")
    ap_cfg = cfg.get("ap", {})
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ap_cfg.get("ssid", "Irrigation-Setup"), password=ap_cfg.get("password", "setup1234"))
    serial_log.log("Setup-AP aktiv: " + ap.ifconfig()[0])
    return "ap", ap.ifconfig()[0]
