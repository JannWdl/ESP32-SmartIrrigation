"""Bounded asynchronous HTTP requests; slow clients cannot hold the control loop."""

import json

try: import asyncio

except ImportError: import uasyncio as asyncio

from settings import validate

STATIC_FILES={'/': ('index.html', 'text/html; charset=utf-8', 'no-cache', '287ea1cc2e1ce32d'), '/ui.5488754f1f67.css': ('ui.5488754f1f67.css', 'text/css; charset=utf-8', 'public, max-age=31536000, immutable', '5488754f1f671d00'), '/ui.1959ae6e4ef8.js': ('ui.1959ae6e4ef8.js', 'text/javascript; charset=utf-8', 'public, max-age=31536000, immutable', '1959ae6e4ef8eb3f')}

class Web:

    def __init__(self,app):

        self.app=app; self.clients=0; self.server=None

    async def start(self,port=80):

        self.server=await asyncio.start_server(self.handle,'0.0.0.0',port,backlog=3)

    async def send(self,w,data,status=200,ctype='application/json'):

        if not isinstance(data,bytes):

            data=(json.dumps(data,separators=(',',':')) if ctype=='application/json' else data).encode()

        w.write(('HTTP/1.1 %d OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n' % (status,ctype,len(data))).encode())

        await asyncio.wait_for_ms(w.drain(),2000)

        for i in range(0,len(data),1024):

            w.write(data[i:i+1024]); await asyncio.wait_for_ms(w.drain(),2000)

    async def send_static(self,w,info,headers,head_only=False):
        import os
        name,ctype,cache,digest=info
        accepted=headers.get('accept-encoding','').split(',')
        compressed=any(p.strip().split(';')[0]=='gzip' and not any(q.strip() in ('q=0','q=0.0','q=0.00','q=0.000') for q in p.split(';')[1:]) for p in accepted)
        path=self.app.code+'/'+name+('.gz' if compressed else '')
        tag='"'+digest+('-gz' if compressed else '')+'"'
        common='ETag: %s\r\nCache-Control: %s\r\nVary: Accept-Encoding\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n'%(tag,cache)
        if tag in [t.strip() for t in headers.get('if-none-match','').split(',')]:
            w.write(('HTTP/1.1 304 Not Modified\r\n'+common+'\r\n').encode())
            await asyncio.wait_for_ms(w.drain(),2000)
            return
        size=os.stat(path)[6]
        extra='Content-Encoding: gzip\r\n' if compressed else ''
        w.write(('HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n'%(ctype,size)+extra+common+'\r\n').encode())
        await asyncio.wait_for_ms(w.drain(),2000)
        if head_only:return
        buffer=bytearray(1024);view=memoryview(buffer)
        with open(path,'rb') as f:
            while True:
                count=f.readinto(buffer)
                if not count:break
                w.write(view[:count])
                await asyncio.wait_for_ms(w.drain(),2000)

    async def read(self,r,length):

        body=b''

        while len(body)<length:

            chunk=await asyncio.wait_for_ms(r.read(min(512,length-len(body))),2000)

            if not chunk: raise ValueError('Anfrage unvollstaendig')

            body+=chunk

        return body

    async def line(self,r,limit):

        result=b''

        while len(result)<=limit:

            byte=await r.read(1) # Caller bounds the whole line; avoid one timer task per byte.

            if not byte: raise ValueError('Header unvollstaendig')

            result+=byte

            if byte==b'\n': return result

        raise ValueError('Header zu lang')

    async def handle(self,r,w):

        if self.clients>=3:

            w.close(); return

        self.clients+=1

        try:

            first=await asyncio.wait_for_ms(self.line(r,256),3000)

            if len(first)>256: raise ValueError('URL zu lang')

            method,path,_=first.decode().strip().split()

            headers={}; total=0

            while True:

                line=await asyncio.wait_for_ms(self.line(r,512),3000); total+=len(line)

                if total>2048 or len(line)>512: raise ValueError('Header zu gross')

                if line==b'\r\n': break

                if not line: raise ValueError('Header unvollstaendig')

                key,value=line.decode().split(':',1); headers[key.lower()]=value.strip()

            length=int(headers.get('content-length','0'))

            if length<0 or 'transfer-encoding' in headers: raise ValueError('Transferformat ungueltig')

            clean=path.split('?',1)[0]

            if method=='POST':

                # No CORS and a required non-simple header block cross-origin browser writes.

                if headers.get('x-irrigation')!='local':

                    await self.send(w,dict(ok=False,error='Anfrage nicht erlaubt'),403); return

                origin=headers.get('origin')

                if origin and origin!='http://'+headers.get('host',''):

                    await self.send(w,dict(ok=False,error='Fremder Ursprung'),403); return

            if method in ('GET','HEAD') and clean in STATIC_FILES:
                await self.send_static(w,STATIC_FILES[clean],headers,method=='HEAD')
                return

            if method=='GET':

                if clean=='/api/status': result=self.app.status()

                elif clean=='/api/config': result=self.app.cfg

                elif clean=='/api/history': result=self.app.history
                elif clean=='/api/history-view':
                    result=dict(history=self.app.history,events=self.app.controller.events)
                elif clean=='/api/overview':
                    result=self.app.status()
                    result['events']=result['events'][-5:]
                    if path.split('?',1)[-1]=='config=1':
                        result['ui']=dict(safety=dict(max_total_day_ml=self.app.cfg['safety']['max_total_day_ml']),
                            channels=[dict(id=c['id'],name=c['name'],threshold=c['threshold'],
                                portion_ml=c['portion_ml'],max_day_ml=c['max_day_ml']) for c in self.app.cfg['channels']])

                else:

                    await self.send(w,dict(ok=False,error='Nicht gefunden'),404); return

                await self.send(w,result); return

            if method!='POST':

                await self.send(w,dict(ok=False,error='Methode ungueltig'),405); return

            if clean=='/api/update/file':

                if '?name=' not in path: raise ValueError('Dateiname fehlt')

                name=path.split('?name=',1)[1]

                target=self.app.updater.target(name,length)

                self.app.updater.uploading=True

                try:

                    with open(target,'wb') as f:

                        remaining=length

                        while remaining:

                            chunk=await asyncio.wait_for_ms(r.read(min(512,remaining)),3000)

                            if not chunk: raise ValueError('Upload unvollstaendig')

                            f.write(chunk); remaining-=len(chunk)

                    self.app.updater.verify_file(name)

                finally:

                    self.app.updater.uploading=False

                await self.send(w,dict(ok=True)); return

            if length>12000: raise ValueError('Anfrage zu gross')

            body=await self.read(r,length)

            data=json.loads(body.decode()) if body else {}

            if not isinstance(data,dict): raise ValueError('JSON-Objekt erforderlich')

            if clean=='/api/config':

                validate(data)

                if self.app.controller.active: raise ValueError('Pumpe zuerst stoppen')

                self.app.controller.maintenance=True

                self.app.config_store.save(data)

                result=dict(ok=True,reboot=True)

            elif clean=='/api/action': result=self.app.action(data)

            elif clean=='/api/update/begin': result=self.app.updater.begin(data)

            elif clean=='/api/update/commit': result=self.app.updater.commit()

            else:

                await self.send(w,dict(ok=False,error='Nicht gefunden'),404); return

            await self.send(w,result,200 if result.get('ok') else 409)

            if result.get('reboot'): asyncio.create_task(self.app.reboot())

        except (ValueError,KeyError,TypeError) as exc:

            try: await self.send(w,dict(ok=False,error=str(exc)),400)

            except Exception: pass

        except Exception:

            try: await self.send(w,dict(ok=False,error='Verbindung oder Speicher fehlgeschlagen'),500)

            except Exception: pass

        finally:

            self.clients-=1

            w.close()

            try: await asyncio.wait_for_ms(w.wait_closed(),500)

            except Exception: pass
