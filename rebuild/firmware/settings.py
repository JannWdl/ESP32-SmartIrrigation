"""Validated configuration. New installs never energize an unknown relay."""
import json

VERSION = '4.0.0'

def defaults():
    channel = lambda i: dict(id=i, name='Pflanze %d' % (i + 1), enabled=True,
        sensor_pin=34+i, pump_pin=27-i, active_low=None, hardware_confirmed=False,
        dry_adc=None, wet_adc=None, flow_ml_s=None, auto=False, threshold=35,
        hysteresis=5, portion_ml=10, soak_seconds=300, max_cycle_ml=50,
        max_day_ml=200, max_run_seconds=30, min_rise=2, profile='custom')
    return dict(schema=4, board='esp32', name='Smart Irrigation', setup_done=False,
        wifi=dict(ssid='', password='', ap_password=''),
        mqtt=dict(enabled=False, host='', port=1883, username='', password='',
                  topic='smart_irrigation_v4', interval=60),
        tank=dict(trigger_pin=18, echo_pin=19, full_cm=None, empty_cm=None,
                  stop_cm=None, resume_cm=None, points=[]),
        safety=dict(boot_pause_seconds=60, max_total_day_ml=400),
        channels=[channel(0), channel(1)])

def number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(label + ': ungueltiger Wert')
    return value

def validate(cfg):
    if not isinstance(cfg, dict) or cfg.get('schema') != 4:
        raise ValueError('Konfiguration muss Schema 4 haben')
    if cfg.get('board') not in ('unknown', 'esp32', 'esp32s3'):
        raise ValueError('Unbekannter Boardtyp')
    if not isinstance(cfg.get('name'), str) or not 1 <= len(cfg['name']) <= 48:
        raise ValueError('Name: 1 bis 48 Zeichen')
    outputs = set([13,14,16,17,18,19,21,22,23,25,26,27,32,33]) if cfg['board'] == 'esp32' else set(list(range(4,19)) + [21,38,39,40,41,42])
    inputs = set([32,33,34,35,36,39]) if cfg['board'] == 'esp32' else set(range(4,11))
    used = set()
    def pin(p, allowed):
        if p is None:
            return
        if cfg['board'] == 'unknown' or type(p) is not int or p not in allowed or p in used:
            raise ValueError('GPIO unzulaessig oder doppelt: ' + str(p))
        used.add(p)
    chs = cfg.get('channels', [])
    if not isinstance(chs, list) or not 1 <= len(chs) <= 4:
        raise ValueError('1 bis 4 Kanaele erforderlich')
    ids = set()
    for ch in chs:
        cid = ch.get('id')
        if type(cid) is not int or not 0 <= cid <= 3 or cid in ids:
            raise ValueError('Kanal-ID muss eindeutig sein (0..3)')
        ids.add(cid)
        if not isinstance(ch.get('name'), str) or not 1 <= len(ch['name']) <= 48:
            raise ValueError('Kanalname: 1 bis 48 Zeichen')
        for key in ('enabled', 'auto', 'hardware_confirmed'):
            if type(ch.get(key)) is not bool:
                raise ValueError(key + ': bool erforderlich')
        if ch.get('active_low') is not None and type(ch['active_low']) is not bool:
            raise ValueError('Relaislogik fehlt')
        pin(ch.get('pump_pin'), outputs)
        pin(ch.get('sensor_pin'), inputs)
        for key in ('dry_adc', 'wet_adc'):
            if ch.get(key) is not None:
                number(ch[key], 10, 4085, key)
        if ch.get('flow_ml_s') is not None:
            number(ch['flow_ml_s'], 0.1, 1000, 'Foerdermenge')
        for key, lo, hi in [('threshold',1,95),('hysteresis',1,20),('portion_ml',1,1000),
                            ('soak_seconds',30,86400),('max_cycle_ml',1,5000),
                            ('max_day_ml',1,50000),('max_run_seconds',1,60),('min_rise',1,20)]:
            number(ch.get(key), lo, hi, key)
        if ch['threshold'] + ch['hysteresis'] > 100:
            raise ValueError('Feuchteziel ueber 100%')
        if not ch['portion_ml'] <= ch['max_cycle_ml'] <= ch['max_day_ml']:
            raise ValueError('Portion <= Zykluslimit <= Tageslimit erforderlich')
        if ch['hardware_confirmed'] and (ch.get('active_low') is None or ch.get('pump_pin') is None or ch.get('sensor_pin') is None):
            raise ValueError('Hardware noch unvollstaendig')
        if ch['auto'] and not ready_channel(ch):
            raise ValueError('Kanal zuerst vollstaendig kalibrieren')
    tank = cfg['tank']
    pin(tank.get('trigger_pin'), outputs)
    pin(tank.get('echo_pin'), outputs | inputs)
    keys = ['full_cm','empty_cm','stop_cm','resume_cm']
    for key in keys:
        if tank.get(key) is not None:
            number(tank[key], 2, 350, key)
    if all(tank.get(k) is not None for k in keys):
        if not tank['full_cm'] < tank['resume_cm'] < tank['stop_cm'] <= tank['empty_cm']:
            raise ValueError('Tank: voll < Freigabe < Reserve <= leer (Abstaende)')
    pts = tank.get('points', [])
    if not isinstance(pts, list) or len(pts) > 12:
        raise ValueError('Maximal 12 Tank-Kalibrierpunkte')
    prev = None
    for p in pts:
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError('Tankpunkte: [Abstand_cm, Liter]')
        number(p[0], 2, 350, 'Tankabstand'); number(p[1], 0, 1000, 'Liter')
        if prev and (p[0] <= prev[0] or p[1] >= prev[1]):
            raise ValueError('Tankpunkte: Abstand steigend, Liter fallend')
        prev = p
    number(cfg['safety']['boot_pause_seconds'],30,3600,'Startpause')
    number(cfg['safety']['max_total_day_ml'],1,100000,'Gesamtlimit')
    for k in ('ssid','password','ap_password'):
        if not isinstance(cfg['wifi'].get(k), str) or len(cfg['wifi'][k]) > 64:
            raise ValueError('WLAN-Einstellung ungueltig')
    if cfg['wifi']['ap_password'] and len(cfg['wifi']['ap_password']) < 8:
        raise ValueError('Setup-WLAN-Passwort: mindestens 8 Zeichen')
    mq = cfg['mqtt']
    if type(mq.get('enabled')) is not bool:
        raise ValueError('MQTT enabled: bool erforderlich')
    for k in ('host','username','password','topic'):
        if not isinstance(mq.get(k), str) or len(mq[k]) > 128:
            raise ValueError('MQTT-Einstellung ungueltig')
    if not mq['topic'] or any(c in mq['topic'] for c in ('+','#','\x00',' ')):
        raise ValueError('MQTT-Topic ungueltig')
    if type(mq['port']) is not int: raise ValueError('MQTT-Port muss ganzzahlig sein')
    if mq['enabled'] and not mq['host']: raise ValueError('MQTT-Broker fehlt')
    number(mq['port'],1,65535,'MQTT-Port'); number(mq['interval'],5,3600,'MQTT-Intervall')
    return cfg

def ready_channel(ch):
    return (ch.get('hardware_confirmed') and ch.get('dry_adc') is not None and
            ch.get('wet_adc') is not None and abs(ch['dry_adc']-ch['wet_adc']) >= 100 and
            ch.get('flow_ml_s') is not None)

def ready_tank(t):
    return (t.get('trigger_pin') is not None and t.get('echo_pin') is not None and
            all(t.get(k) is not None for k in ('full_cm','empty_cm','stop_cm','resume_cm')))

def clone(obj):
    return json.loads(json.dumps(obj))
