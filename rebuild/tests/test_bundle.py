import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware'))
from updater import FILES

class BundleTests(unittest.TestCase):
    def test_package_includes_matching_binary_and_text_files(self):
        data=json.loads((ROOT/'smart-irrigation-4.0.2.json').read_text(encoding='utf8'))
        self.assertEqual(set(FILES),{f['name'] for f in data['files']})
        self.assertEqual(len(FILES),len(data['files']))
        for f in data['files']:
            content=base64.b64decode(f['content'],validate=True) if f['encoding']=='base64' else f['content'].encode('utf8')
            # Source checkouts may normalize Python line endings on Windows.
            self.assertEqual(f['size'],len(content))
            self.assertEqual(f['sha256'],hashlib.sha256(content).hexdigest())
            expected=(ROOT/'firmware'/f['name']).read_bytes()
            if f['encoding']=='utf8':self.assertEqual(content.replace(b'\r\n',b'\n'),expected.replace(b'\r\n',b'\n'))
            else:self.assertEqual(content,expected)
            if f['name'].endswith('.gz'):
                self.assertEqual(gzip.decompress(content),(ROOT/'firmware'/f['name'][:-3]).read_bytes())
        self.assertFalse(any(n.startswith(('config.','state.','release.')) for n in FILES))

class ReleaseRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(ROOT/'tools'))
        from app_update import verified_release
        cls.read=staticmethod(verified_release)
    def record(self,seq,active):
        payload=json.dumps({'active':active,'pending':False})
        return dict(sequence=seq,payload=payload,hash=hashlib.sha256(payload.encode()).hexdigest())
    def test_corrupt_newer_pointer_falls_back(self):
        valid=self.record(1,'factory');bad=self.record(2,'bad');bad['hash']='0'*64
        self.assertEqual(self.read([valid,bad])['active'],'factory')
    def test_no_valid_pointer_rejected(self):
        with self.assertRaises(ValueError):self.read([{'sequence':1}])
