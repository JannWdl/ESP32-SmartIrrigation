"""
event_log.py - sehr kleines RAM-sparendes Ring-Log.
Nur die letzten N Ereignisse im RAM, keine Datei-DB.
"""
import time

_events = []
_max_events = 30

def setup(max_events=30):
    global _max_events
    try:
        _max_events = max(5, min(int(max_events), 80))
    except Exception:
        _max_events = 30

def add(kind, message, channel_id=None):
    global _events
    item = {
        "t": int(time.time()),
        "kind": str(kind),
        "msg": str(message)[:96]
    }
    if channel_id is not None:
        item["ch"] = int(channel_id)
    _events.append(item)
    if len(_events) > _max_events:
        _events = _events[-_max_events:]
    print("EVENT:", item)

def list_events():
    return list(_events)

def clear():
    global _events
    _events = []
