import asyncio, gzip, importlib.util, json, pathlib, sys, tempfile, types

ROOT=pathlib.Path(__file__).resolve().parents[1]
asyncio.wait_for_ms=lambda task,ms:asyncio.wait_for(task,ms/1000)
sys.path.insert(0,str(ROOT/'firmware'))
from web_v4 import Web,STATIC_FILES
module=types.SimpleNamespace(Web=Web)

class App:
    code=str(ROOT/'firmware')
    history=[{'t':1,'values':[30]}]
    controller=types.SimpleNamespace(events=[{'t':n,'message':'event '+str(n)} for n in range(40)])
    cfg={'wifi':{'password':'DO_NOT_INCLUDE'},'mqtt':{'password':'SECRET'},
         'safety':{'max_total_day_ml':400},
         'channels':[{'id':0,'name':'Pflanze 1','threshold':35,'portion_ml':10,'max_day_ml':200}]}
    def status(self):return {'events':self.controller.events,'tank':{'safe':True},'active':None}

async def main():
    app=App();web=module.Web(app);await web.start(0)
    port=web.server.sockets[0].getsockname()[1]
    async def request(path,headers=None,method='GET',body=b''):
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        fields={'Host':'127.0.0.1:'+str(port),**(headers or {})}
        if body:fields['Content-Length']=str(len(body))
        writer.write((method+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in fields.items())+'\r\n').encode()+body)
        await writer.drain();raw=await asyncio.wait_for(reader.read(),3)
        writer.close();await writer.wait_closed()
        header,payload=raw.split(b'\r\n\r\n',1)
        lines=header.decode().split('\r\n');status=int(lines[0].split()[1])
        response_headers={k.lower():v.strip() for k,v in (line.split(':',1) for line in lines[1:])}
        return status,response_headers,payload
    manifest={'assets':{route:info[0] for route,info in STATIC_FILES.items() if route!='/'}}
    for path in ['/',*['/'+v for v in manifest['assets'].values()]]:
        status,h,b=await request(path,{'Accept-Encoding':'gzip'})
        assert status==200 and h['content-encoding']=='gzip'
        name='index.html' if path=='/' else path[1:]
        assert gzip.decompress(b)==(ROOT/'firmware'/name).read_bytes()
        status,h304,b304=await request(path,{'Accept-Encoding':'gzip','If-None-Match':h['etag']})
        assert status==304 and not b304
        status,plain,b=await request(path,{'Accept-Encoding':'gzip;q=0'})
        assert status==200 and 'content-encoding' not in plain and b==(ROOT/'firmware'/name).read_bytes()
        status,head,b=await request(path,method='HEAD');assert status==200 and not b
        assert ('immutable' in h['cache-control'])==(path!='/')
    status,h,b=await request('/api/overview?config=1');d=json.loads(b)
    assert len(d['events'])==5 and 'ui' in d and b'DO_NOT_INCLUDE' not in b and b'SECRET' not in b
    status,h,b=await request('/api/overview');assert 'ui' not in json.loads(b)
    status,h,b=await request('/api/status');assert len(json.loads(b)['events'])==40
    status,h,b=await request('/api/history-view');assert len(json.loads(b)['events'])==40
    status,h,b=await request('/api/action',method='POST',body=b'{}');assert status==403
    status,h,b=await request('/api/action',headers={'X-Irrigation':'local','Origin':'http://elsewhere'},method='POST',body=b'{}');assert status==403
    status,h,b=await request('/api/status',headers={'X-Long':'x'*600});assert status==400
    assert web.clients==0
    web.server.close();await web.server.wait_closed()
    print('PASS: gzip/plain/HEAD, caching/304, versioned assets, compact overview without credentials, full history/status compatibility, POST origin protections and header bounds')

import unittest
class PerformanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_static_cache_and_compact_api(self):await main()
