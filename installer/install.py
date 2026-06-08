#!/usr/bin/env python3
"""
Smart Irrigation Installer v2.1

Wichtig:
- config.json wird standardmäßig NICHT überschrieben.
- Damit bleiben WLAN, Telegram, MQTT und Kanäle erhalten.
- Für komplette Werkseinstellung: --reset-config benutzen.
"""
import argparse
import subprocess
import sys
import time
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"

CODE_UPLOAD_ORDER = [
    "storage.py", "config.py", "hardware.py", "irrigation.py", "wifi_manager.py",
     "mqtt_client.py", "ota.py", "setup_portal.py", "webserver.py",
    "index.html",
    "main.py", "boot.py",
]

def run(cmd, check=True):
    print(">", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=check)

def ensure_tools():
    modules = [("esptool", "esptool"), ("mpremote", "mpremote"), ("serial", "pyserial")]
    for mod, pip in modules:
        try:
            __import__(mod)
        except Exception:
            run([sys.executable, "-m", "pip", "install", pip])

def normalize_port(port):
    port = str(port).strip()
    if platform.system().lower().startswith("win"):
        if port.isdigit():
            return "COM" + port
        if port.upper().startswith("COM"):
            return port.upper()
    return port

def get_ports():
    try:
        from serial.tools import list_ports
        return list(list_ports.comports())
    except Exception:
        return []

def print_ports():
    ports = get_ports()
    if not ports:
        print("Keine Ports gefunden.")
    for p in ports:
        print(f"  {p.device:8} {p.description}")

def choose_port(given):
    if given:
        return normalize_port(given)
    print("Gefundene Ports:")
    print_ports()
    return normalize_port(input("COM-Port eingeben, z.B. COM8: ").strip())

def mpremote(port, *args, check=True):
    return run([sys.executable, "-m", "mpremote", "connect", normalize_port(port), *args], check=check)

def flash(port, firmware=None, erase=False):
    port = normalize_port(port)
    if erase:
        run([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port, "erase_flash"])
    if firmware:
        run([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port, "--baud", "460800", "write_flash", "-z", "0x1000", firmware])
    else:
        print("Kein Firmware-Pfad angegeben; Flashen übersprungen.")

def cleanup(port, reset_config=False):
    for name in ["boot.py", "main.py"]:
        mpremote(port, "rm", ":" + name, check=False)
    if reset_config:
        mpremote(port, "rm", ":config.json", check=False)

def upload(port, reset_config=False):
    # Backup-Projekt hatte /lib/ssl.mpy. Wird mit hochgeladen, wenn vorhanden.
    lib_ssl = SRC / "lib" / "ssl.mpy"
    if lib_ssl.exists():
        print("  -> lib/ssl.mpy")
        mpremote(port, "mkdir", ":lib", check=False)
        mpremote(port, "cp", str(lib_ssl), ":lib/ssl.mpy")

    order = list(CODE_UPLOAD_ORDER)
    if reset_config:
        # config.json vor main/boot übertragen
        order.insert(order.index("main.py"), "config.json")

    for name in order:
        path = SRC / name
        print("  ->", name)
        mpremote(port, "cp", str(path), ":" + name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", nargs="?")
    ap.add_argument("--flash", action="store_true")
    ap.add_argument("--skip-flash", action="store_true")
    ap.add_argument("--erase", action="store_true")
    ap.add_argument("--firmware")
    ap.add_argument("--no-cleanup", action="store_true")
    ap.add_argument("--reset-config", action="store_true", help="config.json auf dem ESP32 löschen und Vorlage neu hochladen")
    args = ap.parse_args()

    ensure_tools()
    port = choose_port(args.port)
    print("Verwende Port:", port)

    visible = [p.device.upper() for p in get_ports()]
    if normalize_port(port).upper() not in visible:
        print("WARNUNG: Port nicht in Liste gefunden. Gefundene Ports:")
        print_ports()

    if args.flash and not args.skip_flash:
        flash(port, args.firmware, args.erase)
        time.sleep(2)

    if not args.no_cleanup:
        cleanup(port, reset_config=args.reset_config)

    print("Übertrage Dateien...")
    upload(port, reset_config=args.reset_config)
    print("Fertig.")
    if not args.reset_config:
        print("Hinweis: config.json wurde NICHT überschrieben.")
    else:
        print("Hinweis: config.json wurde zurückgesetzt.")

if __name__ == "__main__":
    main()
