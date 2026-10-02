import copy
import os
import sys
import tempfile
import unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','firmware'))
from controller import Controller,Tank
from settings import defaults,validate
from persistence import Store

class Memory:
    def __init__(self): self.value={}; self.fail=False
    def load(self,*args,**kwargs): return copy.deepcopy(self.value)
    def save(self,v):
        if self.fail: raise OSError('full')
        self.value=copy.deepcopy(v)

class Hardware:
    def __init__(self): self.running=None; self.starts=[]
    def all_off(self): self.running=None
    def on(self,cid):
        if self.running is not None: raise AssertionError('overlap')
        self.running=cid; self.starts.append(cid)

def configured():
    cfg=defaults(); cfg['board']='esp32'; cfg['safety']['boot_pause_seconds']=30
    cfg['tank'].update(trigger_pin=18,echo_pin=19,full_cm=5,empty_cm=35,stop_cm=31,resume_cm=28,points=[[5,10],[35,0]])
    for i,ch in enumerate(cfg['channels']):
        ch.update(sensor_pin=34+i,pump_pin=26+i,active_low=True,hardware_confirmed=True,
                  dry_adc=3500,wet_adc=1500,flow_ml_s=5,soak_seconds=30)
    return validate(cfg)

class Tests(unittest.TestCase):
    def setUp(self):
        self.cfg=configured(); self.hw=Hardware(); self.store=Memory()
        self.c=Controller(self.cfg,self.hw,self.store)
        self.refresh(30000)
    def refresh(self,now,raw=3000,distance=15):
        self.c.now=now
        for _ in range(3): self.c.tank.update(distance,now)
        for ch in self.cfg['channels']: self.c.sample(ch['id'],raw,now)
    def test_unknown_channel_never_operates_first(self):
        with self.assertRaises(ValueError): self.c.start(42,10)
        self.assertIsNone(self.hw.running)
    def test_second_pump_rejected(self):
        self.assertTrue(self.c.start(0,10)['ok'])
        self.assertFalse(self.c.start(1,10)['ok']); self.assertEqual(self.hw.running,0)
    def test_runtime_limit_and_stop(self):
        self.assertFalse(self.c.start(0,200)['ok'])
        self.c.start(0,10); self.c.tick(32000)
        self.assertIsNone(self.hw.running)
    def test_empty_tank_during_run(self):
        self.c.start(0,10)
        self.c.tank.update(32,30010); self.c.tick(30020)
        self.assertIsNone(self.hw.running)
    def test_invalid_tank_stops_immediately(self):
        self.c.start(0,10); self.c.tank.update(None,30001); self.c.tick(30002)
        self.assertIsNone(self.hw.running)
    def test_stale_tank_stops(self):
        self.c.start(0,50); self.c.tick(36001)
        self.assertIsNone(self.hw.running)
    def test_refill_requires_three_stable_readings(self):
        t=self.c.tank; t.update(32,30000)
        t.update(27,30001); t.update(27,30002); self.assertFalse(t.safe)
        t.update(29,30003); t.update(27,30004); t.update(27,30005); self.assertFalse(t.safe)
        t.update(27,30006); self.assertTrue(t.safe)
    def test_stop_latched_and_persisted(self):
        self.c.start(0,10); self.c.stop(); self.assertIsNone(self.hw.running)
        self.assertFalse(self.c.start(1,10)['ok'])
        new=Controller(self.cfg,self.hw,self.store)
        self.assertTrue(new.state['blocked'])
    def test_budgets_reserved_before_power_and_survive_restart(self):
        self.c.start(0,10); self.assertEqual(self.store.value['used']['0'],10)
        self.c.finish('stop')
        new=Controller(self.cfg,self.hw,self.store)
        self.assertEqual(new.state['used']['0'],10)
    def test_disk_full_cannot_power_pump(self):
        self.store.fail=True
        self.assertFalse(self.c.start(0,10)['ok']); self.assertIsNone(self.hw.running)
        self.assertTrue(self.c.storage_error)
    def test_rail_sensor_fault_stops(self):
        self.c.start(0,10); self.c.sample(0,4095,30001)
        self.assertIsNone(self.hw.running); self.assertIn('0',self.c.state['faults'])
    def test_auto_fairness(self):
        for ch in self.cfg['channels']: ch['auto']=True
        self.c.tick(30000); self.assertEqual(self.hw.running,0)
        self.c.tick(32000); self.assertEqual(self.hw.running,1)
    def test_no_rise_latches_fault_after_three_doses(self):
        for n in range(3):
            now=30000+n*40000; self.refresh(now)
            self.assertTrue(self.c.start(0,10)['ok'])
            self.c.now=now+2000; self.c.finish()
            self.refresh(now+33000)
        self.assertEqual(self.c.state['faults']['0'],'keine_feuchtezunahme')
    def test_manual_cannot_bypass_daily_limits(self):
        self.c.state['used']['0']=195
        self.assertEqual(self.c.start(0,10)['error'],'kanal_tageslimit')
        self.c.state['used']={'1':395}
        self.assertEqual(self.c.start(0,10)['error'],'gesamt_tageslimit')
    def test_boot_pause_preserves_budget(self):
        c=Controller(self.cfg,self.hw,self.store)
        self.assertEqual(c.start(0,10)['error'],'startpause')
    def test_invalid_config_pin_collision(self):
        self.cfg['channels'][1]['pump_pin']=26
        with self.assertRaises(ValueError): validate(self.cfg)
    def test_valid_reverse_adc_calibration(self):
        self.cfg['channels'][0].update(dry_adc=1000,wet_adc=3000)
        self.c.sample(0,1500,30000)
        self.assertEqual(self.c.runtime[0]['moisture'],25)
    def test_tank_liters_interpolated(self):
        self.c.tank.update(20,30000)
        self.assertEqual(self.c.tank.status()['liters'],5)
    def test_corrupt_latest_slot_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(d+'/state'); s.save({'x':1}); s.save({'x':2})
            with open(d+'/state.b','w') as f: f.write('{')
            self.assertEqual(Store(d+'/state').load(strict=True),{'x':1})
    def test_both_slots_corrupt_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            for suffix in ('.a','.b'):
                with open(d+'/state'+suffix,'w') as f: f.write('{')
            c=Controller(self.cfg,self.hw,Store(d+'/state'))
            self.assertTrue(c.storage_error); self.assertTrue(c.state['blocked'])
    def test_nonfinite_values_rejected(self):
        self.cfg['channels'][0]['portion_ml']=float('nan')
        with self.assertRaises(ValueError): validate(self.cfg)

if __name__=='__main__': unittest.main()
