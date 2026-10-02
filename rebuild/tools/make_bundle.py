"""Build the complete, SHA-256 checked WLAN application update package."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=('settings.py','persistence.py','controller.py','hardware_v4.py','runtime.py','web_v4.py','mqtt_v4.py','updater.py','index.html')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--version',default='4.0.0'); p.add_argument('--output',type=Path,default=ROOT/'smart-irrigation-4.0.0.json'); args=p.parse_args()
    files=[]
    for name in FILES:
        data=(ROOT/'firmware'/name).read_bytes()
        files.append(dict(name=name,content=data.decode(),sha256=hashlib.sha256(data).hexdigest()))
    args.output.write_text(json.dumps(dict(version=args.version,files=files),ensure_ascii=False))
    print(args.output)

if __name__=='__main__': main()
