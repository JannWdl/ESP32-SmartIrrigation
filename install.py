#!/usr/bin/env python3
"""
install.py - ESP32 Smart Irrigation Installer

Funktionen:
  - installiert/prüft esptool, mpremote und pyserial
  - optional ESP32 mit lokaler MicroPython-Firmware flashen
  - Projektdateien auf den ESP32 kopieren
  - Home-Assistant-Dateien werden NICHT auf den ESP kopiert

Beispiele:
  python install.py
  python install.py COM8
  python install.py COM8 --skip-flash
  python install.py COM8 --bin firmware.bin
  python install.py COM8 --project-dir aktuell

Hinweis:
  Wenn "could not enter raw repl" kommt:
  1. ESP32 kurz per EN/RESET neu starten
  2. Direkt danach dieses Skript erneut starten
  3. Notfalls beim Start BOOT gedrückt halten, bis der Kopiervorgang beginnt
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_PROJECT_DIRS = ["aktuell", "esp32", "src"]

ESP_EXTENSIONS = {".py", ".json", ".html", ".bin", ".mpy"}
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".github",
    ".vscode",
    "home_assistant",
    "custom_components",
    "docs",
}
EXCLUDE_FILES = {
    "install.py",
    "README.md",
    "README_TELEGRAM_HOME_ASSISTANT.md",
    "README_HOME_ASSISTANT_CUSTOM_INTEGRATION.md",
    "mqtt_ha.py",
    "telegram_bot.py",
    "telegram_notify.py",
}


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=check, cwd=str(cwd) if cwd else None)


def ensure_python_package(import_name: str, pip_name: str | None = None) -> None:
    pip_name = pip_name or import_name
    try:
        __import__(import_name)
        return
    except ImportError:
        print(f"Installiere fehlendes Python-Paket: {pip_name}")
        run([sys.executable, "-m", "pip", "install", "--upgrade", pip_name])


def ensure_tools() -> None:
    ensure_python_package("serial", "pyserial")
    ensure_python_package("mpremote", "mpremote")
    ensure_python_package("esptool", "esptool")


def guess_project_dir(explicit: str | None) -> Path:
    if explicit:
        p = (ROOT / explicit).resolve()
        if not p.exists():
            raise SystemExit(f"Projektordner nicht gefunden: {p}")
        return p

    for name in DEFAULT_PROJECT_DIRS:
        p = ROOT / name
        if (p / "main.py").exists():
            return p

    if (ROOT / "main.py").exists():
        return ROOT

    raise SystemExit("Kein Projektordner gefunden. Nutze z.B. --project-dir aktuell")


def list_ports() -> None:
    try:
        from serial.tools import list_ports as lp
        ports = list(lp.comports())
    except Exception:
        ports = []

    if not ports:
        print("Keine seriellen Ports automatisch gefunden.")
        return

    print("Gefundene Ports:")
    for p in ports:
        print(f"  {p.device:12} {p.description}")


def wake_repl(port: str, baud: int) -> None:
    """Versucht laufende main.py/webserver-Schleifen zu unterbrechen."""
    try:
        import serial
        with serial.Serial(port, baudrate=baud, timeout=0.2) as ser:
            ser.write(b"\x03\x03")  # Ctrl-C Ctrl-C
            ser.flush()
            time.sleep(0.25)
    except Exception as exc:
        print(f"Hinweis: Konnte Ctrl-C nicht senden: {exc}")


def mpremote(port: str, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return run([sys.executable, "-m", "mpremote", "connect", port, *args], check=check)


def flash_firmware(port: str, firmware: Path) -> None:
    if not firmware.exists():
        raise SystemExit(f"Firmware nicht gefunden: {firmware}")

    print("\nFlash lösche...")
    run([sys.executable, "-m", "esptool", "--chip", "esp32", "--port", port, "erase_flash"])
    print("\nMicroPython flashen...")
    run([
        sys.executable,
        "-m",
        "esptool",
        "--chip",
        "esp32",
        "--port",
        port,
        "--baud",
        "460800",
        "write_flash",
        "-z",
        "0x1000",
        str(firmware),
    ])
    print("Warte auf Neustart...")
    time.sleep(3)


def iter_esp_files(project_dir: Path) -> Iterable[Path]:
    for path in sorted(project_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(project_dir)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        if path.suffix.lower() in ESP_EXTENSIONS:
            yield path


def mkdir_device(port: str, device_dir: str) -> None:
    if not device_dir or device_dir == ".":
        return
    parts = device_dir.split("/")
    current = ""
    for part in parts:
        current = part if not current else current + "/" + part
        mpremote(port, ["fs", "mkdir", f":{current}"], check=False)


def copy_files(port: str, project_dir: Path, baud: int) -> None:
    files = list(iter_esp_files(project_dir))
    if not files:
        raise SystemExit(f"Keine ESP-Dateien in {project_dir} gefunden.")

    print(f"\nProjektordner: {project_dir}")
    print(f"Kopiere {len(files)} Dateien auf den ESP32...\n")

    wake_repl(port, baud)
    time.sleep(0.3)

    for i, file in enumerate(files, start=1):
        rel = file.relative_to(project_dir).as_posix()
        mkdir_device(port, str(Path(rel).parent).replace("\\", "/"))
        print(f"[{i:02d}/{len(files):02d}] {rel}")
        try:
            mpremote(port, ["fs", "cp", str(file), f":{rel}"])
        except subprocess.CalledProcessError:
            print("\nFehler beim Kopieren.")
            print("Typische Lösung:")
            print("  - ESP32 per EN/RESET neu starten")
            print("  - Webserver darf nicht dauerhaft blockieren")
            print("  - Danach erneut ausführen: python install.py <PORT> --skip-flash")
            raise

    print("\nStarte ESP32 neu...")
    mpremote(port, ["reset"], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="ESP32 Smart Irrigation Installer")
    parser.add_argument("port", nargs="?", help="COM-Port, z.B. COM8 oder /dev/ttyUSB0")
    parser.add_argument("--project-dir", help="Projektordner, Standard: automatisch")
    parser.add_argument("--bin", dest="firmware_bin", help="Lokale MicroPython-Firmware .bin")
    parser.add_argument("--skip-flash", action="store_true", help="Nur Dateien kopieren, nicht flashen")
    parser.add_argument("--baud", type=int, default=115200, help="Serielle Baudrate für Ctrl-C, Standard 115200")
    args = parser.parse_args()

    ensure_tools()

    port = args.port
    if not port:
        list_ports()
        port = input("\nCOM-Port eingeben, z.B. COM8 oder /dev/ttyUSB0: ").strip()
    if not port:
        raise SystemExit("Kein Port angegeben.")

    project_dir = guess_project_dir(args.project_dir)

    if args.firmware_bin and not args.skip_flash:
        flash_firmware(port, Path(args.firmware_bin).resolve())
    else:
        print("\nFlashen wird übersprungen. Nutze --bin firmware.bin, wenn du MicroPython neu flashen willst.")

    copy_files(port, project_dir, args.baud)
    print("\nFertig. Öffne danach die IP des ESP32 im Browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
