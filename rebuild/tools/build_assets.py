"""Precompress browser assets on the PC; the ESP only streams the files."""
import gzip
import hashlib
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def build():
    firmware=ROOT/'firmware'
    source=(ROOT/'ui/index.html').read_text(encoding='utf-8')
    css=re.search(r'<style>(.*?)</style>',source,re.S).group(1).strip()
    javascript=re.search(r'<script>(.*?)</script>',source,re.S).group(1).strip()
    for old in firmware.iterdir():
        if old.is_file() and re.fullmatch(r'ui\.[0-9a-f]{12}\.(js|css)(\.gz)?',old.name):old.unlink()
    assets=[]
    for content,suffix,ctype in [(css,'css','text/css; charset=utf-8'),(javascript,'js','text/javascript; charset=utf-8')]:
        data=content.encode('utf-8');digest=hashlib.sha256(data).hexdigest()[:12]
        name='ui.'+digest+'.'+suffix
        (firmware/name).write_bytes(data)
        (firmware/(name+'.gz')).write_bytes(gzip.compress(data,compresslevel=9,mtime=0))
        assets.append((name,ctype))
    html=re.sub(r'<style>.*?</style>',lambda m:'<link rel="stylesheet" href="/'+assets[0][0]+'">',source,flags=re.S)
    html=re.sub(r'<script>.*?</script>',lambda m:'<script src="/'+assets[1][0]+'" defer></script>',html,flags=re.S)
    data=html.encode('utf-8');(firmware/'index.html').write_bytes(data)
    (firmware/'index.html.gz').write_bytes(gzip.compress(data,compresslevel=9,mtime=0))
    routes={}
    for name,ctype in [('index.html','text/html; charset=utf-8'),*assets]:
        route='/' if name=='index.html' else '/'+name
        cache='no-cache' if route=='/' else 'public, max-age=31536000, immutable'
        routes[route]=(name,ctype,cache,hashlib.sha256((firmware/name).read_bytes()).hexdigest()[:16])
    server=firmware/'web_v4.py'
    text=server.read_text(encoding='utf-8')
    text,count=re.subn(r'(?m)^STATIC_FILES=.*$',lambda m:'STATIC_FILES='+repr(routes),text)
    if count!=1:raise ValueError('Expected exactly one STATIC_FILES definition')
    server.write_bytes(text.encode('utf-8'))
    preview=source.replace("new URLSearchParams(location.search).has('demo')",'true')
    (ROOT/'preview.html').write_bytes(preview.encode('utf-8'))
    return routes

if __name__=='__main__':
    for route,info in build().items():print(route,info[0])
