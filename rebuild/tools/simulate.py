"""Offline deterministic simulation of the real controller, without ESP32 libraries."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'firmware'),str(ROOT/'tests')]
from controller import Controller
from test_controller import configured,Hardware,Memory

cfg=configured()
for ch in cfg['channels']: ch['auto']=True
hw=Hardware(); c=Controller(cfg,hw,Memory()); raw={0:3000,1:3100}
last=None
for second in range(180):
    now=second*1000
    c.tank.update(15 if second<100 else 32,now)
    for cid in raw: c.sample(cid,raw[cid],now)
    active=c.active
    c.tick(now)
    if active and not c.active: raw[active['id']]-=60
    snapshot=(hw.running,c.tank.safe,c.state['blocked'])
    if snapshot!=last:
        print(json.dumps(dict(seconds=second,pump=hw.running,tank_safe=c.tank.safe,used_ml=c.state['used'])))
        last=snapshot
print('Simulation abgeschlossen. Keine echte Hardware angesteuert.')
