"""Build the complete, SHA-256 checked WLAN application update package."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
from build_assets import build

ROOT=Path(__file__).resolve().parents[1]

def main():
    build()
    sys.path.insert(0,str(ROOT/'firmware'))
    from settings import VERSION
    from updater import FILES
    p=argparse.ArgumentParser(); p.add_argument('--version',default=VERSION); p.add_argument('--output',type=Path); args=p.parse_args()
    files=[]
    for name in FILES:
        data=(ROOT/'firmware'/name).read_bytes()
        binary=name.endswith('.gz')
        content=base64.b64encode(data).decode('ascii') if binary else data.decode('utf-8')
        files.append(dict(name=name,content=content,encoding='base64' if binary else 'utf8',size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    output=args.output or ROOT/('smart-irrigation-'+args.version+'.json')
    output.write_bytes(json.dumps(dict(version=args.version,files=files),ensure_ascii=False,separators=(',',':')).encode('utf-8'))
    print(output)

if __name__=='__main__': main()
