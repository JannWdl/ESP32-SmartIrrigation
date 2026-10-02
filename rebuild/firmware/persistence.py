"""Two verified slots; a truncated or interrupted write preserves the last generation."""
import json
try:
    import hashlib
except ImportError:
    import uhashlib as hashlib
try:
    import binascii
except ImportError:
    import ubinascii as binascii


def digest(data):
    return binascii.hexlify(hashlib.sha256(data).digest()).decode()

class Store:
    def __init__(self, prefix):
        self.prefix = prefix
        self.sequence = 0

    def load(self, default=None, strict=False):
        found = []
        exists = False
        for suffix in ('.a', '.b'):
            try:
                with open(self.prefix + suffix) as f:
                    raw = f.read()
                exists = True
                item = json.loads(raw)
                payload = item['payload']
                if item['hash'] == digest(payload.encode()):
                    found.append((item['sequence'], json.loads(payload)))
            except OSError:
                pass
            except Exception:
                exists = True
        if found:
            found.sort(key=lambda x: x[0])
            self.sequence, value = found[-1]
            return value
        if strict and exists:
            raise ValueError('Beide Speicherstaende beschaedigt: ' + self.prefix)
        return default

    def save(self, value):
        payload = json.dumps(value)
        seq = self.sequence + 1
        text = json.dumps(dict(sequence=seq, hash=digest(payload.encode()), payload=payload))
        path = self.prefix + ('.a' if seq % 2 else '.b')
        with open(path, 'w') as f:
            f.write(text)
        with open(path) as f:
            if f.read() != text:
                raise OSError('Speicherpruefung fehlgeschlagen')
        self.sequence = seq
