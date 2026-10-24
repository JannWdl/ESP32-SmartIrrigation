"""Stable USB-installed bootstrap. Do not include in WLAN update packages."""
import sys
import os
import json
import machine

ROOT=''

def read_release():
    # Minimal reader shares the verified two-slot format without importing a release.
    import hashlib
    import binascii
    found=[]
    exists=False
    for suffix in ('.a','.b'):
        try:
            with open('/release'+suffix) as f: item=json.loads(f.read())
            exists=True
            sha=binascii.hexlify(hashlib.sha256(item['payload'].encode()).digest()).decode()
            if sha==item['hash']: found.append((item['sequence'],json.loads(item['payload'])))
        except OSError: pass
        except Exception: exists=True
    if not found:
        if exists: raise RuntimeError('Release-Speicher beschaedigt; USB-Wiederherstellung erforderlich')
        return dict(active='factory',previous=None,pending=False),0
    found.sort(key=lambda x:x[0]); seq,rec=found[-1]
    return rec,seq

def save_release(rec,seq):
    import hashlib
    import binascii
    payload=json.dumps(rec)
    text=json.dumps(dict(sequence=seq+1,payload=payload,hash=binascii.hexlify(hashlib.sha256(payload.encode()).digest()).decode()))
    with open('/release'+('.a' if (seq+1)%2 else '.b'),'w') as f: f.write(text)

try:
    rec,seq=read_release()
    if rec.get('pending') and rec.get('attempted'):
        if not rec.get('previous'): raise RuntimeError('Kein Rollback vorhanden')
        rec['active']=rec['previous']; rec['pending']=False; rec['attempted']=False
        save_release(rec,seq)
        print('Update zurueckgerollt')
    elif rec.get('pending'):
        rec['attempted']=True; save_release(rec,seq)
    active=rec['active']
    if any(c not in '0123456789.-abcdefghijklmnopqrstuvwxyz' for c in active): raise RuntimeError('Releasepfad ungueltig')
    code='/releases/'+active
    sys.path.insert(0,code)
    try: import asyncio
    except ImportError: import uasyncio as asyncio
    from runtime import main
    asyncio.run(main(ROOT,code))
except BaseException as exc:
    print('STARTFEHLER:',exc)
    # A subsequent boot rolls a failed pending release back. Watchdog also resets a hang.
    import time
    time.sleep(2)
    machine.reset()
