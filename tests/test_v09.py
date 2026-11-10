"""v0.9 regression and security tests; all remote services mocked/off."""
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from vega import backup, extensions, store
from vega.main import LOGIN_FAILURES, app

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA_DIR',tmp_path/'workspace')
    monkeypatch.setattr(store,'DB',store.DATA_DIR/'vega.sqlite3')
    monkeypatch.setattr(store,'MEDIA_DIR',store.DATA_DIR/'media')
    LOGIN_FAILURES.clear()
    with TestClient(app) as client:
        setup=client.post('/api/setup',json={'username':'owner','password':'this-is-a-safe-test-password'})
        assert setup.status_code==201,setup.text
        yield client,{'Authorization':'Bearer '+setup.json()['token']},tmp_path


def _img():
    b=io.BytesIO();Image.new('RGB',(32,48),'cyan').save(b,'PNG');return b.getvalue()


def _post():
    return {'model_id':'aria','platform':'Fanvue','title':'Material educațional',
            'caption':'Personaj virtual AI cu informații utile.',
            'rights_confirmed':True,'ai_disclosure':True}


def test_auth_covered_and_no_live_publish(env):
    c,h,_=env
    for route in ['/api/characters','/api/editorial/packs','/api/connectors','/api/deliveries',
                  '/api/analytics','/api/backup/status','/api/security/report','/api/ollama/status']:
        assert c.get(route).status_code==401,route
    assert c.get('/health').json()['version']=='0.9.0'
    assert c.get('/api/connectors',headers=h).json()['live_posting'] is False
    assert c.get('/api/security/report',headers=h).json()['social_publishing'] is False


def test_nine_profiles_and_cross_model_image_rejection(env):
    c,h,_=env
    profiles=c.get('/api/characters',headers=h).json()
    assert len(profiles)==9
    r=c.post('/api/media',headers=h,data={'model_id':'aria'},files={'file':('portrait.png',_img(),'image/png')})
    assert r.status_code==201,r.text
    imageid=r.json()['id']
    wrong=c.put('/api/characters/maya',headers=h,json={'reference_media_id':imageid,'visual_prompt':'A fictional person'})
    assert wrong.status_code==422
    good=c.put('/api/characters/aria',headers=h,json={'reference_media_id':imageid,'visual_prompt':'original adult fantasy portrait','personality':'creative fictional persona'})
    assert good.status_code==200
    prompt=c.get('/api/production/prompt/aria',headers=h,params={'scene':'garden in spring'}).json()
    assert 'garden in spring' in prompt['prompt'] and prompt['reference_media_id']==imageid
    assert prompt['requires_manual_identity_review']


def test_profiles_reject_unknown_model(env):
    c,h,_=env
    assert c.put('/api/characters/not-real',headers=h,json={}).status_code==422
    assert c.get('/api/production/prompt/not-real',headers=h).status_code==404


def test_editorial_templates_remain_drafts(env):
    c,h,_=env
    pack=c.post('/api/editorial/packs',headers=h,json={'model_id':'aria','platform':'Instagram','topic':'summer lifestyle'}).json()
    assert pack['state']=='draft' and not pack['publishable']
    assert pack['source']=='template' and len(pack['output']['hooks'])==3
    p=c.get('/api/editorial/packs',headers=h).json()
    assert len(p)==1 and p[0]['output']['caption']
    assert c.get('/api/posts',headers=h).json()==[] # no auto-created posts


def test_ollama_requires_local_installation(env,monkeypatch):
    c,h,_=env
    monkeypatch.setattr(extensions,'ollama_status',lambda:{'available':False,'models':[]})
    res=c.post('/api/editorial/packs',headers=h,json={'model_id':'aria','platform':'Fanvue','topic':'evening look','use_local_ai':True})
    assert res.status_code==503
    assert c.get('/api/editorial/packs',headers=h).json()==[]


def test_ollama_url_blocked_from_cloud(env,monkeypatch):
    c,h,_=env
    for value in ['https://example.com','http://8.8.8.8:11434','http://localhost:11434/api',
                  'http://user:pass@127.0.0.1:11434']:
        monkeypatch.setenv('VEGA_OLLAMA_URL',value)
        with pytest.raises(ValueError):extensions.safe_local_url()
    monkeypatch.setenv('VEGA_OLLAMA_URL','http://127.0.0.1:11434')
    assert extensions.safe_local_url()=='http://127.0.0.1:11434'


def test_ollama_response_sanitized_and_no_autoapprove(env,monkeypatch):
    c,h,_=env
    monkeypatch.setattr(extensions,'ollama_status',lambda:{'available':True,'models':['local-model'], 'cloud':False})
    monkeypatch.setattr(extensions,'ollama_request',lambda *_args,**_kwargs:{'response':json.dumps({'hooks':['A','B','C'],'caption':'Draft AI local','hashtags':'#AI','cta':'Vezi detalii'})})
    r=c.post('/api/editorial/packs',headers=h,json={'model_id':'maya','platform':'Fanvue','topic':'creative outfit','use_local_ai':True})
    assert r.status_code==201,r.text
    assert r.json()['source']=='ollama-local' and r.json()['state']=='draft'
    assert c.get('/api/posts',headers=h).json()==[]


def test_delivery_requires_approval_and_killswitch(env):
    c,h,_=env
    pid=c.post('/api/posts',headers=h,json=_post()).json()['id']
    assert c.post('/api/deliveries/prepare/'+pid,headers=h).status_code==409
    c.post('/api/posts/'+pid+'/submit',headers=h)
    c.put('/api/settings',headers=h,json={'paused':False})
    c.post('/api/posts/'+pid+'/approve',headers=h)
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    scheduled=c.post('/api/posts/'+pid+'/schedule',headers=h,json={'scheduled_for':future})
    assert scheduled.status_code==200,scheduled.text
    c.put('/api/settings',headers=h,json={'paused':True})
    assert c.post('/api/deliveries/prepare/'+pid,headers=h).status_code==409
    c.put('/api/settings',headers=h,json={'paused':False})
    bundle=c.post('/api/deliveries/prepare/'+pid,headers=h)
    assert bundle.status_code==201,bundle.text
    assert bundle.json()['published'] is False
    assert bundle.json()['payload']['mode']=='manual_export_only'
    assert c.get('/api/connectors',headers=h).json()['connected_accounts']==0
    assert c.get('/api/deliveries',headers=h).json()[0]['status']=='prepared_offline'
    edit=c.put('/api/posts/'+pid,headers=h,json={**_post(),'caption':'Schimbat - revocă aprobarea'})
    assert edit.status_code==200
    assert c.get('/api/deliveries',headers=h).json()[0]['status']=='invalidated'


def test_delivery_rejects_unconfirmed_rights(env):
    c,h,_=env
    pid=c.post('/api/posts',headers=h,json={**_post(),'rights_confirmed':False}).json()['id']
    c.post('/api/posts/'+pid+'/submit',headers=h)
    c.put('/api/settings',headers=h,json={'paused':False})
    assert c.post('/api/posts/'+pid+'/approve',headers=h).status_code==422


def test_manual_analytics_aggregated_and_updated(env):
    c,h,_=env
    metric={'model_id':'aria','platform':'Fanvue','report_date':'2026-10-01',
            'impressions':200,'clicks':20,'subscribers':2,'gross_cents':999,'cost_cents':250}
    a=c.post('/api/analytics/manual',headers=h,json=metric)
    assert a.status_code==201,a.text
    metric['gross_cents']=1200
    assert c.post('/api/analytics/manual',headers=h,json=metric).status_code==201
    result=c.get('/api/analytics',headers=h).json()
    assert result['sample_size']==1
    assert result['totals']['net_cents']==950
    assert result['data_source']=='manual_only' and not result['real_time']


def test_metrics_invalid(env):
    c,h,_=env
    metric={'model_id':'aria','platform':'TikTok','report_date':'2026-10-01',
            'impressions':1,'clicks':2,'subscribers':0,'gross_cents':0,'cost_cents':0}
    assert c.post('/api/analytics/manual',headers=h,json=metric).status_code==422
    metric['clicks']=0
    metric['gross_cents']=-5
    assert c.post('/api/analytics/manual',headers=h,json=metric).status_code==422
    metric['gross_cents']=0
    metric['report_date']='2029-01-01'
    assert c.post('/api/analytics/manual',headers=h,json=metric).status_code==422


def test_backup_verify_and_safe_restore(env):
    c,h,tmp=env
    c.post('/api/media',headers=h,data={'model_id':'aria'},files={'file':('portrait.png',_img(),'image/png')})
    c.post('/api/posts',headers=h,json=_post())
    save=c.post('/api/backup/create',headers=h)
    assert save.status_code==201,save.text
    name=save.json()['filename']
    assert save.json()['sensitive'] is True
    verified=c.get('/api/backup/verify/'+name,headers=h)
    assert verified.status_code==200,verified.text
    assert verified.json()['valid'] is True and verified.json()['files']>=2
    archive=Path(save.json()['path'])
    dest=tmp/'restored'
    report=backup.restore_offline(archive,dest,confirm=False)
    assert report['dry_run'] and not dest.exists()
    report=backup.restore_offline(archive,dest,confirm=True)
    assert report['valid'] and (dest/'vega.sqlite3').exists()
    assert list((dest/'media').glob('*.png'))
    with pytest.raises(ValueError):backup.restore_offline(archive,dest,confirm=True)


def test_backup_rejects_malicious_entries(env):
    c,h,tmp=env
    archive=tmp/'untrusted.zip'
    manifest={'version':1,'created_at':'now','items':{'../evil.txt':{'sha256':'bad','size':3}}}
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('../evil.txt','bad')
        z.writestr('manifest.json',json.dumps(manifest))
    with pytest.raises(ValueError):backup.verify_backup(archive)


def test_backup_rejects_tampered_content(env):
    c,h,tmp=env
    original=Path(c.post('/api/backup/create',headers=h).json()['path'])
    modified=tmp/'tampered.zip'
    with zipfile.ZipFile(original) as r, zipfile.ZipFile(modified,'w') as w:
        for name in r.namelist():w.writestr(name,b'corrupted' if name=='data/vega.sqlite3' else r.read(name))
    with pytest.raises(ValueError):backup.verify_backup(modified)


def test_security_report_and_whisper_optin(env,monkeypatch):
    c,h,_=env
    report=c.get('/api/security/report',headers=h).json()
    assert report['backup_requires_local_pc'] and report['external_server'] is False
    monkeypatch.delenv('VEGA_WHISPER_MODEL_PATH',raising=False)
    captions=c.get('/api/captions/status',headers=h).json()
    assert captions['available'] is False and captions['model_downloads'] is False
    assert c.post('/api/media/bogus/transcribe',headers=h).status_code==503
