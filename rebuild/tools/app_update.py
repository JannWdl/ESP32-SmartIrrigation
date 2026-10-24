"""Stage a v4 USB application update while retaining configuration and budgets."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from build_assets import build

ROOT=Path(__file__).resolve().parents[1]

def verified_release(records):
    valid=[]
    for record in records:
        try:
            if hashlib.sha256(record['payload'].encode()).hexdigest()==record['hash']:
                valid.append((record['sequence'],json.loads(record['payload'])))
        except (KeyError,ValueError,TypeError):pass
    if not valid:raise ValueError('Kein gültiger V4-Release-Zeiger; zuerst USB-Erstinstallation prüfen')
    return max(valid,key=lambda x:x[0])[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('port')
    parser.add_argument('--pump-power-disconnected',action='store_true')
    args=parser.parse_args()
    if not args.pump_power_disconnected:parser.error('Pumpenversorgung trennen und --pump-power-disconnected angeben')
    build();sys.path.insert(0,str(ROOT/'firmware'))
    from updater import FILES
    from mpremote.transport_serial import SerialTransport
    backup=ROOT/'usb-backup'/time.strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
    tr=SerialTransport(args.port,115200,wait=1)
    try:
        for _ in range(12):tr.serial.write(b'\x03');time.sleep(.12)
        tr.enter_raw_repl(soft_reset=True)
        tr.exec('import machine,os,gc,json,hashlib,binascii;gc.collect();update_watchdog=machine.WDT(timeout=30000)')
        records=[]
        present=json.loads(tr.exec("print(json.dumps(os.listdir('/')))").decode())
        for name in ('release.a','release.b','config.a','config.b','state.a','state.b','main.py','boot.py'):
            if name not in present:continue
            tr.exec('update_watchdog.feed()')
            data=tr.fs_readfile('/'+name)
            (backup/name).write_bytes(data)
            if name.startswith('release.'):records.append(json.loads(data))
        release=verified_release(records)
        if release.get('pending'):raise ValueError('Vorheriges Update ist noch nicht erfolgreich gestartet')
        previous=release['active']
        if not previous or any(c not in '0123456789.-abcdefghijklmnopqrstuvwxyz' for c in previous):
            raise ValueError('Ungültiger Releasepfad')
        stage='usb-'+time.strftime('%Y%m%d-%H%M%S');base='/releases/'+stage
        tr.exec('os.mkdir('+repr(base)+')')
        for name in FILES:
            data=(ROOT/'firmware'/name).read_bytes();target=base+'/'+name
            tr.exec('f=open('+repr(target)+",'wb');gc.collect();update_watchdog.feed()")
            for offset in range(0,len(data),256):tr.exec('f.write('+repr(data[offset:offset+256])+');update_watchdog.feed()')
            tr.exec("f.close()\ndef file_hash(path):\n h=hashlib.sha256()\n with open(path,'rb') as inp:\n  while True:\n   b=inp.read(512)\n   if not b:break\n   h.update(b);update_watchdog.feed()\n return binascii.hexlify(h.digest()).decode()")
            actual=tr.exec('print(file_hash('+repr(target)+'))').decode().strip()
            if actual!=hashlib.sha256(data).hexdigest():raise ValueError('Dateiprüfung fehlgeschlagen: '+name)
            print('Geprüft:',name)
        # These files are never written. Check the stored copies before changing the release pointer.
        for name in ('config.a','config.b','state.a','state.b'):
            if (backup/name).exists():
                actual=tr.exec('print(file_hash('+repr('/'+name)+'))').decode().strip()
                if actual!=hashlib.sha256((backup/name).read_bytes()).hexdigest():raise ValueError('Einstellungen während des Updates verändert')
        tr.exec('import sys;sys.path.insert(0,'+repr('/releases/'+previous)+')\nfrom persistence import Store\nStore(\'/release\').save('+repr(dict(active=stage,previous=previous,pending=True,attempted=False))+')')
        print('Anwendung aktualisiert; Einstellungen und Wasserbudgets erhalten. Sicherung:',backup)
    finally:
        try:tr.exit_raw_repl();tr.serial.write(b'\x04')
        finally:tr.close()

if __name__=='__main__':main()
