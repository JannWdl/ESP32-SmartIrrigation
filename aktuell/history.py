import os
import time
import ustruct

LOG_FILE = "history.bin"
TMP_FILE = "history.tmp"
DAY_S = 86400
REC = ">IBBH"
REC_SIZE = 8

K_MOISTURE = 1
K_WATER = 2
K_ERROR = 3


def now():
    return int(time.time())


def append(kind, channel, value):
    try:
        with open(LOG_FILE, "ab") as f:
            f.write(ustruct.pack(REC, now(), kind & 255, channel & 255, int(value) & 65535))
    except Exception:
        pass


def prune():
    cutoff = now() - DAY_S
    try:
        with open(LOG_FILE, "rb") as src, open(TMP_FILE, "wb") as dst:
            while True:
                b = src.read(REC_SIZE)
                if len(b) != REC_SIZE:
                    break
                ts, kind, ch, val = ustruct.unpack(REC, b)
                if ts >= cutoff:
                    dst.write(b)
        os.remove(LOG_FILE)
        os.rename(TMP_FILE, LOG_FILE)
    except OSError:
        try:
            os.remove(TMP_FILE)
        except OSError:
            pass


def recent(limit=96):
    items = []
    try:
        with open(LOG_FILE, "rb") as f:
            while True:
                b = f.read(REC_SIZE)
                if len(b) != REC_SIZE:
                    break
                ts, kind, ch, val = ustruct.unpack(REC, b)
                items.append((ts, kind, ch, val))
                if len(items) > limit:
                    items.pop(0)
    except OSError:
        pass
    return items
