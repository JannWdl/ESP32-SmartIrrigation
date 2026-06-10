"""
storage.py - sichere JSON Speicherung für MicroPython.
"""
import json
import os

CONFIG_PATH = "/config.json"

def deep_merge(defaults, current):
    if isinstance(defaults, list):
        # Listen nicht hart mergen, aber sicherstellen, dass eine Liste existiert.
        return current if isinstance(current, list) else defaults
    if not isinstance(defaults, dict):
        return current
    if not isinstance(current, dict):
        current = {}
    result = {}
    for k, v in defaults.items():
        result[k] = deep_merge(v, current.get(k)) if k in current else v
    for k, v in current.items():
        if k not in result:
            result[k] = v
    return result

def read_json(path, fallback=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as exc:
        print("WARN JSON read:", path, exc)
        return fallback

def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    try:
        os.remove(path)
    except Exception:
        pass
    os.rename(tmp, path)
    return True
