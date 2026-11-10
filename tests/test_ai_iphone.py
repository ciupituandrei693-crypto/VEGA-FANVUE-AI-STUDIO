"""Offline tests: fake ComfyUI only. No cloud, GPU, or social publishing."""
from __future__ import annotations

import io
import ipaddress
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from cryptography import x509

from vega import ai_engine, store
from vega.main import app, LOGIN_FAILURES


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(store, 'DB', tmp_path / 'vega.sqlite3')
    monkeypatch.setattr(store, 'MEDIA_DIR', tmp_path / 'media')
    LOGIN_FAILURES.clear()
    with TestClient(app) as t:
        yield t


@pytest.fixture
def auth(client):
    r = client.post('/api/setup', json={'username': 'admin', 'password':'some-good-password-123'})
    assert r.status_code == 201
    return client, {'Authorization': 'Bearer ' + r.json()['token']}


class FakeComfy:
    def __init__(self):
        self.graph = None
        self.kind = 'image'
        self.should_fail = False
        self.uploaded = False

    def status(self):
        return {'connected':True, 'devices':['Mock device, not a real GPU'], 'endpoint':'http://127.0.0.1:8188'}

    def checkpoints(self):
        return ['local-demo.safetensors']

    def enqueue(self, workflow):
        self.graph = workflow
        return '1d5a1eaf-52ee-4eea-ac5a-93840d18cf40'

    def history(self, prompt_id):
        if self.should_fail:
            return {prompt_id:{'status':{'status_str':'error','completed':False},'outputs':{}}}
        filename = 'vega.mp4' if self.kind == 'video' else 'vega.png'
        return {prompt_id:{'status':{'status_str':'success','completed':True},
            'outputs':{'9':{'videos' if self.kind == 'video' else 'images':[
                {'filename':filename,'subfolder':'','type':'output'}]}}}}

    def download_output(self, metadata):
        if self.kind == 'video':
            return b'\0\0\0\x18ftypisom00000000000000000000000'  # test header only
        buf=io.BytesIO()
        Image.new('RGB',(64,64),'purple').save(buf,format='PNG')
        return buf.getvalue()

    def upload_image(self, filename, data):
        self.uploaded = True
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
        return 'vega_src.png'


def test_ai_requires_login_and_informs_when_unavailable(client, monkeypatch):
    from vega import main
    class Missing:
        def status(self): raise ai_engine.ComfyUnavailable('ComfyUI indisponibil')
        def checkpoints(self): raise ai_engine.ComfyUnavailable('ComfyUI indisponibil')
    monkeypatch.setattr(main, '_comfy_client', Missing)
    assert client.get('/api/ai/status').status_code == 401
    r=client.post('/api/setup',json={'username':'admin','password':'some-good-password-123'})
    h={'Authorization':'Bearer '+r.json()['token']}
    assert client.get('/api/ai/status',headers=h).json()['connected'] is False
    assert client.get('/api/ai/checkpoints',headers=h).status_code == 503
    assert client.post('/api/ai/generate',headers=h,json={
        'model_id':'aria','mode':'image','prompt':'an adult fashion studio portrait'}).status_code == 503


def test_ai_photo_queued_and_result_is_private(auth, monkeypatch):
    from vega import main
    t,h=auth
    fake=FakeComfy()
    monkeypatch.setattr(main,'_comfy_client',lambda:fake)
    status=t.get('/api/ai/status',headers=h).json()
    assert status['connected'] and not status['cloud_enabled']
    assert t.get('/api/ai/checkpoints',headers=h).json()['checkpoints']==['local-demo.safetensors']
    create=t.post('/api/ai/generate',headers=h,json={
        'model_id':'aria','mode':'image','checkpoint':'local-demo.safetensors',
        'prompt':'fictional adult model in a well-lit studio', 'width':512,'height':768})
    assert create.status_code==202,create.text
    assert fake.graph['1']['inputs']['ckpt_name']=='local-demo.safetensors'
    assert t.post('/api/ai/generate',headers=h,json={'model_id':'maya','mode':'image','prompt':'a fictional portrait of an adult woman'}).status_code==409
    assert 'fashion' not in fake.graph['2']['inputs']['text']
    job=create.json()['id']
    assert t.get('/api/ai/jobs').status_code==401
    result=t.get('/api/ai/jobs/'+job,headers=h)
    assert result.status_code==200,result.text
    mediaid=result.json()['media_id']
    assert result.json()['state']=='complete'
    assert t.get('/api/media/'+mediaid+'/download').status_code==401
    content=t.get('/api/media/'+mediaid+'/download',headers=h).content
    assert content[:8] == b'\x89PNG\r\n\x1a\n'
    listing=t.get('/api/media',headers=h).json()
    assert any(x['origin']=='ai_image' and x['model_id']=='aria' for x in listing)
    assert t.get('/api/ai/jobs/'+job,headers=h).json()['media_id']==mediaid
    assert t.get('/api/settings',headers=h).json()['publisher_enabled'] is False


def test_ai_failed_job_does_not_create_media(auth,monkeypatch):
    from vega import main
    t,h=auth
    fake=FakeComfy();fake.should_fail=True
    monkeypatch.setattr(main,'_comfy_client',lambda:fake)
    a=t.post('/api/ai/generate',headers=h,json={'model_id':'aria','mode':'image',
        'prompt':'fictional adult model fashion photograph'}).json()
    b=t.get('/api/ai/jobs/'+a['id'],headers=h).json()
    assert b['state']=='failed' and not b['media_id']
    assert t.get('/api/media',headers=h).json()==[]


def test_video_workflow_import_and_cross_model_source_isolation(auth,monkeypatch):
    from vega import main
    t,h=auth
    fake=FakeComfy();fake.kind='video'
    monkeypatch.setattr(main,'_comfy_client',lambda:fake)
    workflow={'1':{'class_type':'CLIPTextEncode','inputs':{'text':'__VEGA_PROMPT__','clip':['2',0]}},
              '2':{'class_type':'LoadImage','inputs':{'image':'__VEGA_IMAGE__'}},
              '3':{'class_type':'SaveVideo','inputs':{'filename_prefix':'test','video':['1',0]}}}
    file=('video.json',json.dumps(workflow).encode(),'application/json')
    r=t.post('/api/ai/workflow/video',headers=h,files={'file':file})
    assert r.status_code==200,r.text
    img=io.BytesIO();Image.new('RGB',(50,70),'blue').save(img,format='PNG')
    media=t.post('/api/media',headers=h,data={'model_id':'aria'},
        files={'file':('input.png',img.getvalue(),'image/png')}).json()['id']
    bad=t.post('/api/ai/generate',headers=h,json={'model_id':'maya','mode':'video',
        'prompt':'fictional adult model walking at sunset','source_media_id':media})
    assert bad.status_code==422
    good=t.post('/api/ai/generate',headers=h,json={'model_id':'aria','mode':'video',
        'prompt':'fictional adult model walking at sunset','source_media_id':media})
    assert good.status_code==202,good.text
    assert fake.uploaded and fake.graph['2']['inputs']['image']=='vega_src.png'
    assert fake.graph['1']['inputs']['text']=='fictional adult model walking at sunset'
    job=good.json()['id']
    result=t.get('/api/ai/jobs/'+job,headers=h)
    assert result.status_code==200,result.text
    assert result.json()['state']=='complete'
    items=t.get('/api/media',headers=h).json()
    assert any(x['origin']=='ai_video' and x['mime_type']=='video/mp4' for x in items)


def test_invalid_ai_workflows_and_checkpoints(auth,monkeypatch):
    from vega import main
    t,h=auth
    monkeypatch.setattr(main,'_comfy_client',lambda:FakeComfy())
    assert t.post('/api/ai/workflow/video',headers=h,files={'file':('gui.json',
        json.dumps({'nodes':[{'type':'CLIPTextEncode'}]}).encode(),'application/json')}).status_code==422
    r=t.post('/api/ai/generate',headers=h,json={
        'model_id':'aria','mode':'image','checkpoint':'not-installed',
        'prompt':'fictional adult model photographed indoors'})
    assert r.status_code==503
    assert t.post('/api/ai/generate',headers=h,json={
        'model_id':'aria','mode':'image','source_media_id':'abc',
        'prompt':'fictional adult model photographed indoors'}).status_code==422
    assert t.post('/api/ai/generate',headers=h,json={
        'model_id':'unknown','mode':'image','prompt':'fictional adult model indoors'}).status_code==404


def test_comfy_url_not_configurable_and_result_validation():
    assert ai_engine.COMFY_HOST=='127.0.0.1'
    assert ai_engine.ComfyClient().port==8188
    with pytest.raises(ai_engine.ComfyInvalid):
        ai_engine.ComfyClient().download_output({'filename':'../../secret'})
    with pytest.raises(ai_engine.ComfyInvalid):
        ai_engine.validate_generated(b'not an image','image','.png')
    with pytest.raises(ai_engine.ComfyInvalid):
        ai_engine.validate_generated(b'not a video','video','.mp4')
    graph=ai_engine.photo_workflow('local.safetensors','fashion image','bad',512,768)
    assert graph['7']['class_type']=='SaveImage'
    with pytest.raises(ai_engine.ComfyInvalid):
        ai_engine.photo_workflow('local.safetensors','image','',255,768)


def test_tls_certificate_generation_and_no_ca_private_key(tmp_path,monkeypatch):
    from scripts import create_lan_cert as certs
    monkeypatch.setattr(certs,'DIR',tmp_path/'lan_certs')
    ca,leaf,key=certs.generate('192.168.10.25')
    assert ca.exists() and leaf.exists() and key.exists()
    assert not (certs.DIR/'VEGA-CA.key').exists()
    cert=x509.load_pem_x509_certificate(leaf.read_bytes())
    names=cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert ipaddress.ip_address('192.168.10.25') in names.get_values_for_type(x509.IPAddress)
    root=x509.load_der_x509_certificate(ca.read_bytes())
    assert root.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True
    assert certs.generate('192.168.10.25')==(ca,leaf,key)
    with pytest.raises(RuntimeError):
        certs.generate('192.168.10.26')
    with pytest.raises(ValueError):
        certs.generate('8.8.8.8')
    with pytest.raises(ValueError):
        certs.generate('127.0.0.1')


def test_lan_mode_enforces_https_host_and_no_remote_setup(tmp_path):
    code='''from fastapi.testclient import TestClient
from vega.main import app
with TestClient(app,base_url="https://192.168.44.25",client=("192.168.44.10",3456)) as c:
 assert c.get("/health").status_code == 200
 assert c.post("/api/setup",json={"username":"owner","password":"strong-password-123"}).status_code == 403
 assert c.get("http://192.168.44.25/health").status_code == 403
 assert c.get("https://evil.example/health").status_code == 400
print("HTTPS LAN checks passed")'''
    env={**os.environ,'VEGA_LAN_MODE':'1','VEGA_LAN_IP':'192.168.44.25',
         'VEGA_DATA_DIR':str(tmp_path/'lan'),
         'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
    r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env,timeout=20)
    assert r.returncode==0,r.stderr+r.stdout


def test_pwa_does_not_cache_private_api():
    root=Path(__file__).resolve().parents[1]
    sw=(root/'web/sw.js').read_text()
    assert "url.pathname.startsWith('/assets/')" in sw
    assert "cache" in sw.lower()
    assert '/api/' not in (sw.split('const ASSETS = ')[1].split(';')[0])
    assert (root/'START_VEGA_IPHONE_HTTPS.bat').exists()
    assert (root/'docs/IPHONE_HTTPS_LAN_v0_4.md').exists()
