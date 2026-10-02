"""Fresh USB installation on an ESP32 already running MicroPython."""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description='Pumpenversorgung vor USB-Installation trennen. Bestehende v3-Konfiguration wird nicht importiert.')
    p.add_argument('port',help='z.B. COM8 oder /dev/ttyUSB0')
    p.add_argument('--pump-power-disconnected',action='store_true',help='Pumpenversorgung wurde physisch getrennt')
    args=p.parse_args()
    if not args.pump_power_disconnected:
        p.error('Zuerst Pumpenversorgung trennen, dann --pump-power-disconnected angeben.')
    def remote(*parts,check=True):
        return subprocess.run([sys.executable,'-m','mpremote','connect',args.port,*parts],check=check)
    with tempfile.TemporaryDirectory() as d:
        # Preserve the original installation's config separately; new schema starts clean.
        for name in ('config.json','config.a','config.b','state.a','state.b','release.a','release.b','main.py','boot.py'):
            result=subprocess.run([sys.executable,'-m','mpremote','connect',args.port,'fs','cp',':/'+name,str(Path(d)/name)],capture_output=True)
            if result.returncode==0:
                backup=ROOT/'usb-backup'; backup.mkdir(exist_ok=True)
                import shutil
                shutil.copy2(Path(d)/name,backup/name)
        remote('exec',"import os\nfor p in ('/releases','/releases/factory'):\n try: os.mkdir(p)\n except OSError: pass")
        for f in sorted((ROOT/'firmware').iterdir()):
            if f.is_file() and f.suffix in ('.py','.html'):
                remote('fs','cp',str(f),':/releases/factory/'+f.name)
        # A fresh install intentionally starts without imported config/state/release pointers.
        remote('exec',"import os\nfor p in ('/config.a','/config.b','/state.a','/state.b','/release.a','/release.b'):\n try: os.remove(p)\n except OSError: pass")
        remote('fs','cp',str(ROOT/'tools'/'bootstrap.py'),':/main.py')
        empty=Path(d)/'boot.py'; empty.write_text('# Smart Irrigation 4 starts from main.py\n')
        remote('fs','cp',str(empty),':/boot.py')
        remote('reset')
    print('Installiert. Setup-WLAN Irrigation-xxxxxx verbinden und http://192.168.4.1 öffnen.')
    print('Alte Dateien soweit vorhanden gesichert in rebuild/usb-backup; erst Hardware prüfen und kalibrieren.')

if __name__=='__main__': main()
