import asyncio
import hashlib
import json
import os
import sys
import tempfile
import unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','firmware'))
from updater import Updater,FILES
from persistence import Store
from web_v4 import Web
from mqtt_v4 import packet,utf
from test_controller import configured,Hardware,Memory
from controller import Controller

async def wait_ms(coro,ms): return await asyncio.wait_for(coro,ms/1000)
asyncio.wait_for_ms=wait_ms

class Reader:
    def __init__(self,data): self.data=data
    async def read(self,n):
        out=self.data[:n]; self.data=self.data[n:]; return out
class Writer:
    def __init__(self): self.data=b''; self.closed=False
    def write(self,data): self.data+=data
    async def drain(self): pass
    def close(self): self.closed=True
    async def wait_closed(self): pass

class WebApp:
    def __init__(self): self.actions=[]
    def action(self,data): self.actions.append(data); return {'ok':True}
    def status(self): return {'ok':True,'blocked':False}

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def send(self,data):
        app=WebApp(); w=Writer(); web=Web(app)
        await web.handle(Reader(data),w)
        self.assertTrue(w.closed); self.assertEqual(web.clients,0)
        return app,w
    async def test_cross_origin_write_rejected(self):
        app,w=await self.send(b'POST /api/action HTTP/1.1\r\nHost: esp\r\nOrigin: http://evil\r\nX-Irrigation: local\r\nContent-Length: 17\r\n\r\n{"action":"stop"}')
        self.assertIn(b'403',w.data); self.assertFalse(app.actions)
    async def test_missing_custom_header_rejected(self):
        app,w=await self.send(b'POST /api/action HTTP/1.1\r\nContent-Length: 0\r\n\r\n')
        self.assertIn(b'403',w.data); self.assertFalse(app.actions)
    async def test_valid_action_dispatched(self):
        body=b'{"action":"stop"}'
        app,w=await self.send(b'POST /api/action HTTP/1.1\r\nHost: esp\r\nOrigin: http://esp\r\nX-Irrigation: local\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)
        self.assertEqual(app.actions,[{'action':'stop'}]); self.assertIn(b'200',w.data)
    async def test_long_header_bounded(self):
        app,w=await self.send(b'GET /api/status HTTP/1.1\r\nFoo: '+b'x'*600+b'\r\n\r\n')
        self.assertIn(b'400',w.data)
    async def test_incomplete_json_rejected(self):
        app,w=await self.send(b'POST /api/action HTTP/1.1\r\nX-Irrigation: local\r\nContent-Length: 30\r\n\r\n{}')
        self.assertIn(b'400',w.data); self.assertFalse(app.actions)
    async def test_huge_json_rejected_without_reading(self):
        app,w=await self.send(b'POST /api/action HTTP/1.1\r\nX-Irrigation: local\r\nContent-Length: 500000\r\n\r\n')
        self.assertIn(b'400',w.data); self.assertFalse(app.actions)

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=self.temp.name
        os.mkdir(self.root+'/releases')
        self.c=Controller(configured(),Hardware(),Memory(),now=100)
        self.u=Updater(self.root,self.c)
        self.files=[dict(name=n,size=3,sha256=hashlib.sha256(b'abc').hexdigest()) for n in FILES]
    def tearDown(self): self.temp.cleanup()
    def fill(self):
        for n in FILES:
            with open(self.u.stage+'/'+n,'wb') as f: f.write(b'abc')
    def test_missing_file_manifest_rejected_and_pumps_locked(self):
        with self.assertRaises(ValueError): self.u.begin({'version':'4.0.0','files':self.files[:-1]})
        self.assertTrue(self.c.state['blocked']); self.assertTrue(self.c.maintenance)
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError): self.u.begin({'version':'../../oops','files':self.files})
    def test_bad_hash_cannot_activate_release(self):
        self.u.begin({'version':'4.0.0','files':self.files}); self.fill()
        with open(self.u.stage+'/runtime.py','wb') as f: f.write(b'bad')
        with self.assertRaises(ValueError): self.u.commit()
        self.assertIsNone(Store(self.root+'/release').load())
    def test_complete_release_staged_with_rollback(self):
        self.u.begin({'version':'4.0.0','files':self.files}); self.fill()
        self.assertTrue(self.u.commit()['reboot'])
        rec=Store(self.root+'/release').load(strict=True)
        self.assertTrue(rec['pending']); self.assertFalse(rec['attempted']); self.assertEqual(rec['previous'],'factory')
        with self.assertRaises(ValueError): self.u.commit()
    def test_wrong_upload_size_rejected(self):
        self.u.begin({'version':'4.0.0','files':self.files})
        with self.assertRaises(ValueError): self.u.target('runtime.py',4)
    def test_concurrent_upload_rejected(self):
        self.u.begin({'version':'4.0.0','files':self.files}); self.u.uploading=True
        with self.assertRaises(ValueError): self.u.target('runtime.py',3)
    def test_mqtt_length_encoding(self):
        self.assertEqual(packet(0x30,b'x'*128)[:3],b'\x30\x80\x01')
        self.assertEqual(utf('ä'),b'\x00\x02\xc3\xa4')

if __name__=='__main__': unittest.main()
