"""Deterministic local controller, independent of networking and wall-clock changes."""
from settings import ready_channel, ready_tank

class Tank:
    def __init__(self, cfg):
        self.cfg = cfg
        self.safe = False
        self.distance = None
        self.last_ms = None
        self.good = 0
        self.reason = 'nicht_kalibriert'

    def update(self, distance, now):
        self.last_ms = now
        self.distance = distance
        t = self.cfg
        if distance is None or not 2 <= distance <= 350:
            self.safe = False; self.good = 0; self.reason = 'sensorfehler'
        elif not ready_tank(t):
            self.safe = False; self.good = 0; self.reason = 'nicht_kalibriert'
        elif distance > t['empty_cm'] + 2 or distance < t['full_cm'] - 2:
            self.safe = False; self.good = 0; self.reason = 'ausserhalb_kalibrierung'
        elif distance >= t['stop_cm']:
            self.safe = False; self.good = 0; self.reason = 'wasserreserve'
        elif not self.safe:
            self.good = self.good + 1 if distance <= t['resume_cm'] else 0
            if self.good >= 3:
                self.safe = True; self.reason = 'ok'
            else:
                self.reason = 'warte_auf_stabile_freigabe'
        else:
            self.reason = 'ok'

    def fresh(self, now):
        if self.last_ms is None or now - self.last_ms > 6000:
            self.safe = False; self.good = 0; self.reason = 'messung_veraltet'
        return self.safe

    def status(self):
        d = self.distance; t = self.cfg
        percent = None; liters = None
        if d is not None and ready_tank(t):
            percent = round(max(0,min(100,(t['empty_cm']-d)*100/(t['empty_cm']-t['full_cm']))),1)
            pts = t.get('points', [])
            if len(pts) >= 2:
                if d <= pts[0][0]: liters = pts[0][1]
                elif d >= pts[-1][0]: liters = pts[-1][1]
                else:
                    for a,b in zip(pts,pts[1:]):
                        if a[0] <= d <= b[0]:
                            liters = a[1] + (d-a[0])*(b[1]-a[1])/(b[0]-a[0]); break
        return dict(safe=self.safe, reason=self.reason, distance_cm=d, percent=percent,
                    liters=None if liters is None else round(liters,2))

class Controller:
    def __init__(self, cfg, hw, store, now=0):
        self.cfg=cfg; self.hw=hw; self.store=store; self.tank=Tank(cfg['tank'])
        self.boot=now; self.now=now; self.active=None; self.maintenance=False
        self.dirty=False; self.save_at=now; self.round_robin=0; self.events=[]
        try:
            saved=store.load({}, strict=True)
            self.state=dict(blocked=saved.get('blocked',False),
                            used=saved.get('used',{}), elapsed_ms=saved.get('elapsed_ms',0),
                            faults=saved.get('faults',{}))
            self.storage_error=False
        except Exception:
            self.state=dict(blocked=True,used={},elapsed_ms=0,faults={})
            self.storage_error=True
        self.runtime={ch['id']:dict(moisture=None, raw=None, sampled=None,
            wait_until=now+cfg['safety']['boot_pause_seconds']*1000,
            baseline=None, cycle_ml=0, doses=0, reason='startpause', pending=False)
            for ch in cfg['channels']}
        self.last_tick=now
        hw.all_off()
        self.event('boot','Startpause; Pumpen aus')

    def event(self, kind, message, cid=None):
        self.events.append(dict(t=self.now//1000,kind=kind,message=message,id=cid))
        self.events=self.events[-40:]

    def persist(self):
        try:
            self.store.save(self.state); self.dirty=False; self.save_at=self.now
            return True
        except Exception:
            self.storage_error=True; self.state['blocked']=True
            self.hw.all_off(); self.active=None
            self.event('error','Speicherfehler: Bewaesserung gesperrt')
            return False

    def channel(self, cid):
        for ch in self.cfg['channels']:
            if ch['id'] == cid: return ch
        raise ValueError('Unbekannte Kanal-ID')

    def fault(self,cid,why):
        key=str(cid)
        if self.state['faults'].get(key) != why:
            self.state['faults'][key]=why; self.dirty=True
            self.event('error',why,cid)
        if self.active and self.active['id']==cid: self.finish(why)

    def sample(self,cid,raw,now):
        ch=self.channel(cid); r=self.runtime[cid]
        r['raw']=raw; r['sampled']=now
        if raw is None or not 10 <= raw <= 4085:
            r['moisture']=None
            if ch['hardware_confirmed']: self.fault(cid,'boden_sensorfehler')
            return
        if ch.get('dry_adc') is None or ch.get('wet_adc') is None or abs(ch['dry_adc']-ch['wet_adc'])<100:
            r['moisture']=None; return
        pct=(ch['dry_adc']-raw)*100/(ch['dry_adc']-ch['wet_adc'])
        r['moisture']=round(max(0,min(100,pct)),1)
        if r['baseline'] is not None and not (self.active and self.active['id']==cid) and now >= r['wait_until']:
            if r['pending']:
                r['pending']=False
                if r['moisture']-r['baseline'] >= ch['min_rise']:
                    r['baseline']=r['moisture']; r['doses']=0
                elif r['doses']>=3:
                    self.fault(cid,'keine_feuchtezunahme')
            if r['moisture']>=ch['threshold']+ch['hysteresis']:
                r['baseline']=None; r['cycle_ml']=0; r['doses']=0

    def reason(self,ch,now,calibration=False):
        cid=ch['id']; r=self.runtime[cid]
        if self.storage_error: return 'speicherfehler'
        if self.state['blocked']: return 'global_gesperrt'
        if self.maintenance: return 'wartung'
        if now-self.boot < self.cfg['safety']['boot_pause_seconds']*1000: return 'startpause'
        if not ch['enabled']: return 'deaktiviert'
        if self.state['faults'].get(str(cid)): return self.state['faults'][str(cid)]
        if not self.tank.fresh(now): return 'tank_'+self.tank.reason
        if not ch['hardware_confirmed']: return 'hardware_nicht_bestaetigt'
        if calibration: return None
        if not ready_channel(ch): return 'nicht_kalibriert'
        if r['moisture'] is None or r['sampled'] is None or now-r['sampled']>6000: return 'boden_messung_ungueltig'
        if now<r['wait_until']: return 'einwirkzeit'
        return None

    def start(self,cid,ml,source='manual',seconds=None):
        ch=self.channel(cid); r=self.runtime[cid]; now=self.now
        if self.active: return dict(ok=False,error='pumpe_bereits_aktiv')
        calibration=source=='calibration'
        why=self.reason(ch,now,calibration)
        if why: return dict(ok=False,error=why)
        if calibration:
            if ch['auto']: return dict(ok=False,error='automatik_fuer_kalibrierung_deaktivieren')
            if type(seconds) not in (int,float) or not 0.5<=seconds<=min(5,ch['max_run_seconds']):
                return dict(ok=False,error='kalibrierung_maximal_5_sekunden')
            ml=ch['max_cycle_ml']  # Conservative reservation while flow is unknown.
        else:
            if isinstance(ml,bool) or not isinstance(ml,(int,float)) or not 1<=ml<=ch['max_cycle_ml']:
                return dict(ok=False,error='menge_ungueltig')
            seconds=ml/ch['flow_ml_s']
            if seconds>ch['max_run_seconds']: return dict(ok=False,error='laufzeitlimit')
        if r['cycle_ml']+ml>ch['max_cycle_ml']: return dict(ok=False,error='zykluslimit')
        used=self.state['used']; key=str(cid)
        if used.get(key,0)+ml>ch['max_day_ml']: return dict(ok=False,error='kanal_tageslimit')
        if sum(used.values())+ml>self.cfg['safety']['max_total_day_ml']: return dict(ok=False,error='gesamt_tageslimit')
        used[key]=used.get(key,0)+ml
        if not self.persist(): return dict(ok=False,error='speicherfehler')
        r['cycle_ml']+=ml; r['doses']+=1; r['pending']=not calibration
        if r['baseline'] is None: r['baseline']=r['moisture']
        self.active=dict(id=cid,end=now+int(seconds*1000),start=now,ml=ml,source=source)
        try:
            self.hw.on(cid)
        except Exception:
            self.finish('hardwarefehler'); self.fault(cid,'hardwarefehler')
            return dict(ok=False,error='hardwarefehler')
        self.event('water','Start: %s ml reserviert (%s)' % (ml,source),cid)
        return dict(ok=True,id=cid,ml_reserved=ml,seconds=round(seconds,2))

    def finish(self,reason='fertig'):
        if not self.active: return
        job=self.active; self.hw.all_off(); self.active=None
        self.runtime[job['id']]['wait_until']=self.now+self.channel(job['id'])['soak_seconds']*1000
        if job['source']=='calibration':
            r=self.runtime[job['id']]; r['baseline']=None; r['cycle_ml']=0; r['doses']=0; r['pending']=False
        self.event('water','Stopp: '+reason,job['id'])

    def stop(self):
        self.hw.all_off(); self.finish('globaler_stopp')
        self.state['blocked']=True; self.dirty=True; self.persist()
        self.event('stop','Alle Pumpen und Automatik gesperrt')
        return dict(ok=True)

    def release(self,cid=None):
        if self.active: return dict(ok=False,error='pumpe_aktiv')
        if self.storage_error: return dict(ok=False,error='speicherfehler')
        if cid is None: self.state['blocked']=False
        else:
            self.channel(cid); self.state['faults'].pop(str(cid),None)
            r=self.runtime[cid]; r['baseline']=None; r['cycle_ml']=0; r['doses']=0; r['pending']=False
        self.dirty=True
        return dict(ok=self.persist())

    def tick(self,now,allow_auto=True):
        elapsed=max(0,now-self.last_tick); self.last_tick=now; self.now=now
        self.state['elapsed_ms']+=elapsed
        if self.active:
            job=self.active
            r=self.runtime[job['id']]
            if now>=job['end']: self.finish()
            elif not self.tank.fresh(now): self.finish('tank_'+self.tank.reason)
            elif r['sampled'] is None or now-r['sampled']>6000 or r['raw'] is None:
                self.finish('boden_messung_veraltet')
        if self.active: return
        if self.state['elapsed_ms']>=86400000:
            self.state['elapsed_ms']=0; self.state['used']={}; self.dirty=True
            self.event('budget','Neues 24-Stunden-Budget')
        if self.dirty or now-self.save_at>=600000:
            if not self.persist(): return
        if not allow_auto: return
        chs=self.cfg['channels']
        for offset in range(len(chs)):
            idx=(self.round_robin+offset)%len(chs); ch=chs[idx]; r=self.runtime[ch['id']]
            why=self.reason(ch,now)
            if not why and not ch['auto']: why='automatik_aus'
            if not why and r['moisture']>=ch['threshold'] and r['baseline'] is None: why='feucht_genug'
            if not why and r['moisture']>=ch['threshold']+ch['hysteresis']: why='feucht_genug'
            r['reason']=why or 'trocken'
            if not why:
                res=self.start(ch['id'],ch['portion_ml'],'auto')
                if res['ok']:
                    self.round_robin=(idx+1)%len(chs); break
                r['reason']=res['error']
                if res['error']=='zykluslimit': self.fault(ch['id'],'zykluslimit_erreicht')

    def status(self):
        return dict(blocked=self.state['blocked'],storage_error=self.storage_error,
            active=self.active,tank=self.tank.status(),used_total_ml=sum(self.state['used'].values()),
            budget_hours_remaining=round((86400000-self.state['elapsed_ms'])/3600000,2),
            channels=[dict(id=ch['id'],name=ch['name'],auto=ch['auto'],
                moisture=self.runtime[ch['id']]['moisture'],raw=self.runtime[ch['id']]['raw'],
                reason=self.runtime[ch['id']]['reason'],fault=self.state['faults'].get(str(ch['id'])),
                wait_seconds=max(0,(self.runtime[ch['id']]['wait_until']-self.now)//1000),
                used_ml=self.state['used'].get(str(ch['id']),0)) for ch in self.cfg['channels']],
            events=self.events)
