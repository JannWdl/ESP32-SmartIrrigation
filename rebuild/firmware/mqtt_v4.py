"""Small async MQTT 3.1.1 client. Commands are QoS 0 and never retained."""
import json
try: import asyncio
except ImportError: import uasyncio as asyncio


def utf(text):
    data=text.encode(); return bytes((len(data)>>8,len(data)&255))+data

def packet(kind,body):
    length=len(body); head=bytes((kind,))
    while True:
        byte=length%128; length//=128
        head+=bytes((byte|128 if length else byte,))
        if not length: break
    return head+body

class MQTT:
    def __init__(self,app,uid):
        self.app=app; self.cfg=app.cfg['mqtt']; self.uid=uid
        self.reader=None; self.writer=None; self.connected=False; self.error=''
        self.lock=asyncio.Lock(); self.last_event=None

    async def send(self,data):
        async with self.lock:
            self.writer.write(data)
            await asyncio.wait_for_ms(self.writer.drain(),1500)

    async def publish(self,topic,payload,retain=False):
        if not isinstance(payload,str): payload=json.dumps(payload)
        await self.send(packet(0x31 if retain else 0x30,utf(topic)+payload.encode()))

    async def frame(self):
        header=await asyncio.wait_for_ms(self.reader.readexactly(1),70000)
        length=0; factor=1
        for _ in range(4):
            b=(await asyncio.wait_for_ms(self.reader.readexactly(1),2000))[0]
            length+=(b&127)*factor; factor*=128
            if not b&128: break
        else: raise ValueError('MQTT length')
        if length>10000: raise ValueError('MQTT packet too large')
        body=await asyncio.wait_for_ms(self.reader.readexactly(length),2000) if length else b''
        return header[0],body

    async def discovery(self):
        base=self.cfg['topic']; ident='irrigation_'+self.uid
        device=dict(identifiers=[ident],name=self.app.cfg['name'],manufacturer='JannWdl',model='Smart Irrigation 4',sw_version='4.0.0')
        async def entity(domain,name,key,template=None,extra=None):
            data=dict(name=name,unique_id=ident+'_'+key,device=device,
                availability_topic=base+'/availability',payload_available='online',payload_not_available='offline')
            if template:
                data.update(state_topic=base+'/state',value_template=template)
            if extra: data.update(extra)
            await self.publish('homeassistant/'+domain+'/'+ident+'/'+key+'/config',data,True)
            await asyncio.sleep_ms(10)
        await entity('sensor','Wasservorrat','tank_liters','{{ value_json.tank.liters }}',dict(unit_of_measurement='L',state_class='measurement'))
        await entity('sensor','Tankfüllstand','tank_percent','{{ value_json.tank.percent }}',dict(unit_of_measurement='%',state_class='measurement'))
        await entity('binary_sensor','Wasser nachfüllen oder Sensor prüfen','tank_problem',"{{ 'ON' if not value_json.tank.safe else 'OFF' }}",dict(device_class='problem'))
        await entity('binary_sensor','Bewässerung gesperrt','blocked',"{{ 'ON' if value_json.blocked else 'OFF' }}")
        await entity('button','Alles stoppen','stop',extra=dict(command_topic=base+'/command',payload_press='{"action":"stop"}'))
        await entity('button','Automatik freigeben','release',extra=dict(command_topic=base+'/command',payload_press='{"action":"release"}'))
        for idx,ch in enumerate(self.app.cfg['channels']):
            prefix='ch_'+str(ch['id']); template='{{ value_json.channels['+str(idx)+'].moisture }}'
            await entity('sensor',ch['name']+' Bodenfeuchtigkeit',prefix+'_moisture',template,dict(unit_of_measurement='%',state_class='measurement'))
            await entity('sensor',ch['name']+' Status',prefix+'_reason','{{ value_json.channels['+str(idx)+'].reason }}')
            await entity('button',ch['name']+' Wasserportion',prefix+'_water',extra=dict(command_topic=base+'/command',payload_press=json.dumps(dict(action='run',id=ch['id'],ml=ch['portion_ml']))))
            await entity('switch',ch['name']+' Automatik',prefix+'_auto',"{{ 'ON' if value_json.channels["+str(idx)+"].auto else 'OFF' }}",dict(command_topic=base+'/command',payload_on=json.dumps(dict(action='auto',id=ch['id'],enabled=True)),payload_off=json.dumps(dict(action='auto',id=ch['id'],enabled=False))))

    async def receive(self):
        while self.connected:
            kind,body=await self.frame()
            if kind>>4!=3: continue
            if len(body)<2: raise ValueError('MQTT publish')
            n=(body[0]<<8)|body[1]
            if n+2>len(body): raise ValueError('MQTT topic')
            topic=body[2:2+n].decode(); payload=body[2+n:]
            if topic=='homeassistant/status' and payload==b'online':
                await self.discovery(); continue
            if topic!=self.cfg['topic']+'/command': continue
            # Retained or QoS>0 commands may be redelivered: never execute them.
            if kind&7 or len(payload)>512: continue
            try:
                data=json.loads(payload.decode())
                if not isinstance(data,dict): raise ValueError('Befehl muss ein Objekt sein')
                if data.get('action') not in ('run','stop','release','clear','auto'):
                    raise ValueError('Befehl ungueltig')
                result=self.app.action(data)
            except Exception as exc: result=dict(ok=False,error=str(exc))
            await self.publish(self.cfg['topic']+'/result',result)

    async def transmit(self):
        state_due=0; ping_due=0
        while self.connected:
            now=self.app.clock.now()
            if now>=state_due:
                await self.publish(self.cfg['topic']+'/state',self.app.status())
                state_due=now+self.cfg['interval']*1000
            events=self.app.controller.events
            if events:
                start=0
                if self.last_event is not None:
                    for i,event in enumerate(events):
                        if event is self.last_event: start=i+1; break
                for event in events[start:]:
                    await self.publish(self.cfg['topic']+'/event',event)
                    self.last_event=event
            if now>=ping_due:
                await self.send(b'\xc0\x00'); ping_due=now+20000
            await asyncio.sleep(1)

    async def run(self):
        while True:
            if not self.cfg['enabled'] or not self.app.wlan.isconnected() or self.app.controller.active:
                await asyncio.sleep(2); continue
            receiver=None; transmitter=None
            try:
                # DNS may block in MicroPython. Only initiate a connection with all pumps off.
                self.reader,self.writer=await asyncio.wait_for_ms(asyncio.open_connection(self.cfg['host'],self.cfg['port']),5000)
                flags=0x02|0x04|0x20 # clean session, will, retained will
                payload=utf('irrigation-'+self.uid)+utf(self.cfg['topic']+'/availability')+utf('offline')
                if self.cfg['username']:
                    flags|=0x80; payload+=utf(self.cfg['username'])
                    if self.cfg['password']: flags|=0x40; payload+=utf(self.cfg['password'])
                await self.send(packet(0x10,utf('MQTT')+bytes((4,flags,0,60))+payload))
                kind,body=await self.frame()
                if kind!=0x20 or body!=b'\x00\x00': raise ValueError('MQTT Anmeldung fehlgeschlagen')
                await self.send(packet(0x82,b'\x00\x01'+utf(self.cfg['topic']+'/command')+b'\x00'+utf('homeassistant/status')+b'\x00'))
                self.connected=True; self.error=''
                await self.publish(self.cfg['topic']+'/availability','online',True)
                await self.discovery()
                receiver=asyncio.create_task(self.receive()); transmitter=asyncio.create_task(self.transmit())
                # Both must remain alive; propagate failures through await.
                await asyncio.gather(receiver,transmitter)
            except Exception as exc:
                self.error=str(exc)
            finally:
                self.connected=False
                for task in (receiver,transmitter):
                    if task: task.cancel()
                if self.writer:
                    self.writer.close()
                    try: await asyncio.wait_for_ms(self.writer.wait_closed(),500)
                    except Exception: pass
                self.reader=None; self.writer=None
            await asyncio.sleep(10)
