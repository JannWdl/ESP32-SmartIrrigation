"""Local sensing and control run independently of Wi-Fi/MQTT availability."""
import time
import gc
import json
import machine
import network
import os
try: import asyncio
except ImportError: import uasyncio as asyncio
from settings import defaults,validate,clone,VERSION
from persistence import Store
from hardware_v4 import Hardware
from controller import Controller
from web_v4 import Web
from mqtt_v4 import MQTT
from updater import Updater

class Clock:
    def __init__(self): self.previous=time.ticks_ms(); self.ms=0
    def now(self):
        current=time.ticks_ms(); self.ms+=max(0,time.ticks_diff(current,self.previous)); self.previous=current
        return self.ms

class Application:
    def __init__(self,root,code):
        self.root=root; self.code=code; self.clock=Clock()
        self.config_store=Store(root+'/config')
        self.config_error=''
        try: self.cfg=validate(self.config_store.load(defaults(),strict=True))
        except Exception as exc:
            self.cfg=defaults(); self.config_error=str(exc)
        self.hw=Hardware(self.cfg)
        self.controller=Controller(self.cfg,self.hw,Store(root+'/state'))
        if self.config_error:
            self.controller.state['blocked']=True
            self.controller.event('error','Konfiguration ungueltig: neu einrichten')
        self.wlan=network.WLAN(network.STA_IF); self.ap=network.WLAN(network.AP_IF)
        self.control_healthy=False
        self.history=[]; self.web=Web(self); self.updater=Updater(root,self.controller)
        import binascii
        self.uid=binascii.hexlify(machine.unique_id()).decode()
        self.mqtt=MQTT(self,self.uid)

    def status(self):
        data=self.controller.status()
        data.update(version=VERSION,uptime_seconds=self.clock.now()//1000,
                    heap=gc.mem_free(),mqtt=dict(connected=self.mqtt.connected,error=self.mqtt.error),
                    config_error=self.config_error)
        return data

    def action(self,data):
        action=data.get('action'); cid=data.get('id')
        if cid is not None and type(cid) is not int: raise ValueError('Kanal-ID muss eine Zahl sein')
        self.controller.tick(self.clock.now(),allow_auto=False)
        if action=='stop': return self.controller.stop()
        if action=='release': return self.controller.release()
        if action=='clear':
            if cid is None: raise ValueError('Kanal-ID fehlt')
            return self.controller.release(cid)
        if action=='run':
            if cid is None: raise ValueError('Kanal-ID fehlt')
            return self.controller.start(cid,data.get('ml'))
        if action=='calibrate':
            if cid is None: raise ValueError('Kanal-ID fehlt')
            return self.controller.start(cid,None,'calibration',data.get('seconds'))
        if action=='auto':
            if self.controller.active or self.controller.maintenance: return dict(ok=False,error='pumpe_aktiv_oder_wartung')
            enabled=data.get('enabled')
            if type(enabled) is not bool: raise ValueError('enabled muss bool sein')
            self.controller.channel(cid)
            candidate=clone(self.cfg)
            for ch in candidate['channels']:
                if ch['id']==cid: ch['auto']=enabled
            validate(candidate); self.config_store.save(candidate)
            self.controller.channel(cid)['auto']=enabled
            return dict(ok=True)
        if action=='reboot':
            self.controller.stop(); return dict(ok=True,reboot=True)
        raise ValueError('Aktion unbekannt')

    async def reboot(self):
        self.hw.all_off(); self.controller.maintenance=True
        await asyncio.sleep(1); machine.reset()

    async def control(self):
        sensor_due=0; tank_due=0; history_due=0
        watchdog=machine.WDT(timeout=8000)
        while True:
            now=self.clock.now(); self.controller.tick(now)
            if now>=sensor_due:
                for ch in self.cfg['channels']:
                    self.controller.sample(ch['id'],self.hw.raw(ch['id']),now)
                sensor_due=now+2000
            if now>=tank_due:
                # A single timeout is bounded to 22 ms per pulse phase. Never filter away a low tank.
                distance=self.hw.distance()
                previous=self.controller.tank.reason
                self.controller.tank.update(distance,self.clock.now())
                current=self.controller.tank.reason
                if current!=previous:
                    self.controller.event('info' if self.controller.tank.safe else 'error','Tank: '+current)
                tank_due=now+2000
            self.controller.tick(self.clock.now())
            if now>=history_due:
                self.history.append(dict(t=now//1000,values=[self.controller.runtime[c['id']]['moisture'] for c in self.cfg['channels']]))
                self.history=self.history[-288:] # 5-minute samples, 24 hours, bounded RAM
                history_due=now+300000
            self.control_healthy=True
            watchdog.feed()
            await asyncio.sleep_ms(20)

    def setup_ap(self):
        self.ap.active(True)
        password=self.cfg['wifi']['ap_password']
        if password:
            self.ap.config(essid='Irrigation-'+self.uid[-6:],password=password,authmode=3)
        else:
            self.ap.config(essid='Irrigation-'+self.uid[-6:],authmode=0)
        print('Setup-WLAN:',self.ap.ifconfig()[0])

    async def wifi(self):
        self.wlan.active(True)
        attempted=-30000
        while True:
            now=self.clock.now()
            if self.wlan.isconnected():
                if self.ap.active(): self.ap.active(False)
            elif not self.controller.active and now-attempted>=30000:
                attempted=now
                if self.cfg['wifi']['ssid']:
                    try: self.wlan.connect(self.cfg['wifi']['ssid'],self.cfg['wifi']['password'])
                    except Exception: pass
                if not self.ap.active(): self.setup_ap()
            await asyncio.sleep(2)

    async def run(self):
        self.setup_ap()
        await self.web.start()
        # A pending update is healthy only after the control task has run without an exception.
        tasks=[asyncio.create_task(self.control()),asyncio.create_task(self.wifi()),asyncio.create_task(self.mqtt.run())]
        await asyncio.sleep(3)
        if not self.control_healthy: raise RuntimeError('Steuerung nicht gestartet')
        release=Store(self.root+'/release'); rec=release.load(None,strict=True)
        if rec and rec.get('pending'):
            rec['pending']=False; rec['attempted']=False; release.save(rec)
        await asyncio.gather(*tasks)

async def main(root,code):
    app=None
    try:
        app=Application(root,code)
        await app.run()
    finally:
        if app: app.hw.all_off()
