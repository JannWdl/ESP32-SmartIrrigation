"""ESP32-specific I/O. HC-SR04 echo MUST be level-shifted to 3.3 V."""
import time
from machine import Pin, ADC, time_pulse_us

class Hardware:
    def __init__(self,cfg):
        self.pumps={}; self.sensors={}; self.low={}; self.trig=None; self.echo=None
        try:
            for ch in cfg['channels']:
                cid=ch['id']
                if ch['hardware_confirmed']:
                    low=ch['active_low']; self.low[cid]=low
                    self.pumps[cid]=Pin(ch['pump_pin'],Pin.OUT,value=1 if low else 0)
                if ch['sensor_pin'] is not None and cfg['board']!='unknown':
                    adc=ADC(Pin(ch['sensor_pin']))
                    adc.atten(ADC.ATTN_11DB)
                    try: adc.width(ADC.WIDTH_12BIT)
                    except AttributeError: pass
                    self.sensors[cid]=adc
            t=cfg['tank']
            if cfg['board']!='unknown' and t['trigger_pin'] is not None and t['echo_pin'] is not None:
                self.trig=Pin(t['trigger_pin'],Pin.OUT,value=0)
                self.echo=Pin(t['echo_pin'],Pin.IN)
        except Exception:
            self.all_off()
            raise

    def all_off(self):
        for cid,p in self.pumps.items(): p.value(1 if self.low[cid] else 0)

    def on(self,cid):
        self.all_off()  # physical interlock as well as controller interlock
        if cid not in self.pumps: raise ValueError('Pumpenhardware nicht freigegeben')
        self.pumps[cid].value(0 if self.low[cid] else 1)

    def raw(self,cid):
        if cid not in self.sensors: return None
        try:
            vals=[self.sensors[cid].read() for _ in range(5)]; vals.sort()
            return vals[2]
        except Exception:
            return None

    def distance(self):
        if self.trig is None: return None
        self.trig.value(0); time.sleep_us(2)
        self.trig.value(1); time.sleep_us(10); self.trig.value(0)
        try:
            duration=time_pulse_us(self.echo,1,22000)
            if duration<=0: return None
            d=duration*0.0343/2
            return round(d,2) if 2<=d<=350 else None
        except Exception:
            return None
