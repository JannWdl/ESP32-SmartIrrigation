"""Verified staged releases. The stable bootstrap handles failed-start rollback."""
import os
import json
from persistence import digest

FILES=('settings.py','persistence.py','controller.py','hardware_v4.py','runtime.py',
       'web_v4.py','mqtt_v4.py','updater.py','index.html')

class Updater:
    def __init__(self,root,controller):
        self.root=root; self.controller=controller; self.manifest=None; self.stage=None
        self.uploading=False

    def begin(self,manifest):
        if self.uploading: raise ValueError('Upload bereits aktiv')
        self.controller.stop(); self.controller.maintenance=True
        version=manifest.get('version','')
        if not isinstance(version,str) or not version or len(version)>24 or any(c not in '0123456789.-abcdefghijklmnopqrstuvwxyz' for c in version):
            raise ValueError('Version ungueltig')
        files=manifest.get('files',[])
        if len(files)!=len(FILES) or set(f.get('name') for f in files)!=set(FILES):
            raise ValueError('Vollstaendiges Updatepaket erforderlich')
        total=0
        for f in files:
            size=f.get('size'); sha=f.get('sha256','')
            if type(size) is not int or not 1<=size<=48000 or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Manifest ungueltig')
            total+=size
        if total>200000: raise ValueError('Updatepaket zu gross')
        self.stage=self.root+'/releases/update-'+str(self.controller.now)
        os.mkdir(self.stage)
        self.manifest=manifest
        return dict(ok=True)

    def target(self,name,size):
        if self.uploading: raise ValueError('Upload bereits aktiv')
        if self.manifest is None: raise ValueError('Update zuerst beginnen')
        match=[f for f in self.manifest['files'] if f['name']==name]
        if len(match)!=1 or match[0]['size']!=size: raise ValueError('Datei passt nicht zum Manifest')
        return self.stage+'/'+name

    def verify_file(self,name):
        info=[f for f in self.manifest['files'] if f['name']==name][0]
        path=self.stage+'/'+name
        import hashlib
        import binascii
        h=hashlib.sha256()
        with open(path,'rb') as f:
            while True:
                chunk=f.read(512)
                if not chunk: break
                h.update(chunk)
        if os.stat(path)[6]!=info['size'] or binascii.hexlify(h.digest()).decode()!=info['sha256']:
            raise ValueError('Dateipruefung fehlgeschlagen: '+name)

    def commit(self):
        if self.uploading or self.manifest is None: raise ValueError('Update unvollstaendig')
        for f in self.manifest['files']: self.verify_file(f['name'])
        from persistence import Store
        store=Store(self.root+'/release')
        current=store.load({'active':'factory','previous':None,'pending':False})
        store.save(dict(active=self.stage.rsplit('/',1)[-1],previous=current['active'],pending=True,attempted=False))
        self.manifest=None
        return dict(ok=True,reboot=True)
