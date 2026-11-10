from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from vega import store
from vega.main import app, LOGIN_FAILURES

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store,"DATA_DIR",tmp_path)
    monkeypatch.setattr(store,"DB",tmp_path/"test.sqlite3")
    monkeypatch.setattr(store,"MEDIA_DIR",tmp_path/"media")
    LOGIN_FAILURES.clear()
    with TestClient(app) as c: yield c

@pytest.fixture
def authed(client):
    res=client.post('/api/setup',json={"username":"vega_admin","password":"valid-demo-password-123"})
    assert res.status_code==201,res.text
    return client,{"Authorization":"Bearer "+res.json()["token"]}

def example(model="aria",platform="Instagram",rating="sfw",rights=True):
    return {"model_id":model,"platform":platform,"kind":"photo",
            "title":"Ținută de seară","hook":"Un detaliu care schimbă tot",
            "caption":"O fotografie fashion cu personaj virtual AI.",
            "hashtags":"#Fashion #AICreator","cta":"Ce părere ai?", "rating":rating,
            "ai_disclosure":True,"rights_confirmed":rights}

def create(client,headers,payload=None):
    r=client.post('/api/posts',headers=headers,json=payload or example())
    assert r.status_code==201,r.text
    return r.json()['id']

def test_health_setup_login(client):
    assert client.get('/health').json()['external_connections'] is False
    assert client.get('/api/setup-state').json()['configured'] is False
    assert client.get('/api/models').status_code==401
    assert client.post('/api/setup',json={"username":"admin","password":"short"}).status_code==422
    r=client.post('/api/setup',json={"username":"admin","password":"password-123456"})
    assert r.status_code==201
    assert client.post('/api/setup',json={"username":"other","password":"password-123456"}).status_code==409
    assert client.post('/api/login',json={"username":"admin","password":"wrong"}).status_code==401
    r2=client.post('/api/login',json={"username":"admin","password":"password-123456"})
    assert r2.status_code==200
    headers={"Authorization":"Bearer "+r2.json()["token"]}
    assert len(client.get('/api/models',headers=headers).json())==9
    assert client.post('/api/logout',headers=headers).status_code==200
    assert client.get('/api/me',headers=headers).status_code==401

def test_kill_switch_and_approval(authed):
    client,headers=authed
    assert client.get('/api/settings',headers=headers).json()['paused'] is True
    pid=create(client,headers)
    assert client.post(f'/api/posts/{pid}/approve',headers=headers).status_code==423
    assert client.post(f'/api/posts/{pid}/submit',headers=headers).json()['state']=='in_review'
    assert client.post(f'/api/posts/{pid}/approve',headers=headers).status_code==423
    assert client.put('/api/settings',headers=headers,json={'paused':False}).status_code==200
    assert client.post(f'/api/posts/{pid}/approve',headers=headers).json()['state']=='approved'
    assert client.get('/api/dashboard',headers=headers).json()['approved']==1
    assert client.get('/api/settings',headers=headers).json()['publisher_enabled'] is False

def test_approval_requires_rights(authed):
    client,headers=authed
    pid=create(client,headers,example(rights=False))
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    client.put('/api/settings',headers=headers,json={'paused':False})
    assert client.post(f'/api/posts/{pid}/approve',headers=headers).status_code==422
    new=example(rights=True)
    assert client.put(f'/api/posts/{pid}',headers=headers,json=new).json()['state']=='draft'
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    assert client.post(f'/api/posts/{pid}/approve',headers=headers).status_code==200

def test_edit_revokes_approval_and_schedule(authed):
    client,headers=authed
    pid=create(client,headers)
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    client.put('/api/settings',headers=headers,json={'paused':False})
    client.post(f'/api/posts/{pid}/approve',headers=headers)
    future=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    r=client.post(f'/api/posts/{pid}/schedule',headers=headers,json={'scheduled_for':future})
    assert r.status_code==200 and r.json()['published'] is False
    updated=example();updated['caption']='Text actualizat, aprobarea trebuie refăcută.'
    assert client.put(f'/api/posts/{pid}',headers=headers,json=updated).json()['approval_revoked'] is True
    post=client.get('/api/posts',headers=headers).json()[0]
    assert post['state']=='draft' and post['approved_at'] is None and post['scheduled_for'] is None
    assert client.post(f'/api/posts/{pid}/schedule',headers=headers,json={'scheduled_for':future}).status_code==409

def test_schedule_must_be_future_with_timezone(authed):
    client,headers=authed
    pid=create(client,headers)
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    client.put('/api/settings',headers=headers,json={'paused':False})
    client.post(f'/api/posts/{pid}/approve',headers=headers)
    assert client.post(f'/api/posts/{pid}/schedule',headers=headers,json={'scheduled_for':'2030-02-02T09:00:00'}).status_code==422
    assert client.post(f'/api/posts/{pid}/schedule',headers=headers,json={'scheduled_for':'2020-01-01T00:00:00Z'}).status_code==422
    future=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    assert client.post(f'/api/posts/{pid}/schedule',headers=headers,json={'scheduled_for':future}).status_code==200
    assert client.post(f'/api/posts/{pid}/unschedule',headers=headers).json()['state']=='approved'

def test_reject_and_audit(authed):
    client,headers=authed
    pid=create(client,headers)
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    assert client.post(f'/api/posts/{pid}/reject',headers=headers,json={'reason':'Descriere incompletă'}).status_code==200
    assert client.get('/api/posts',headers=headers).json()[0]['state']=='draft'
    logs=client.get('/api/audit',headers=headers).json()
    assert any(x['action']=='post.reject' for x in logs)

def test_adult_content_only_fanvue(authed):
    client,headers=authed
    assert client.post('/api/posts',headers=headers,json=example(platform='Instagram',rating='18+')).status_code==422
    assert client.post('/api/posts',headers=headers,json=example(platform='Fanvue',rating='18+')).status_code==201
    p=example();p['ai_disclosure']=False
    assert client.post('/api/posts',headers=headers,json=p).status_code==422

def test_seo_is_offline(authed):
    client,headers=authed
    r=client.post('/api/seo/suggest',headers=headers,json={'model_id':'liora','platform':'Instagram','topic':'ținute elegante'})
    assert r.status_code==200
    assert len(r.json()['hooks'])==3
    assert 'AI' in r.json()['caption']
    assert 'șabloane' in r.json()['note']
    assert client.post('/api/seo/suggest',headers=headers,json={'model_id':'missing','platform':'X','topic':'look chic'}).status_code==404

def test_media_upload_and_private_download(authed):
    client,headers=authed
    buf=io.BytesIO();Image.new('RGB',(160,200),'#926aab').save(buf,format='PNG');png=buf.getvalue()
    data={'model_id':'aria'}
    files={'file':('look.png',io.BytesIO(png),'image/png')}
    r=client.post('/api/media',headers=headers,data=data,files=files)
    assert r.status_code==201,r.text
    mid=r.json()['id']
    assert client.get(f'/api/media/{mid}/download').status_code==401
    assert client.get(f'/api/media/{mid}/download',headers=headers).content==png
    bad=client.post('/api/media',headers=headers,data=data,
                    files={'file':('fake.png',io.BytesIO(b'NOT A PNG'),'image/png')})
    assert bad.status_code==415

def test_export_does_not_publish(authed):
    client,headers=authed
    pid=create(client,headers)
    client.post(f'/api/posts/{pid}/submit',headers=headers)
    client.put('/api/settings',headers=headers,json={'paused':False})
    client.post(f'/api/posts/{pid}/approve',headers=headers)
    r=client.get('/api/export',headers=headers)
    assert r.status_code==200 and r.json()['published'] is False
    assert len(r.json()['posts'])==1

def test_app_and_assets(client):
    assert 'FANVUE AI STUDIO' in client.get('/').text
    assert client.get('/assets/app.js').status_code==200
    assert client.get('/assets/style.css').status_code==200
    assert client.get('/assets/manifest.webmanifest').status_code==200
    assert "frame-ancestors 'none'" in client.get('/').headers['content-security-policy']


def _upload_image(client,headers,model='aria',name='sample.png'):
    buf=io.BytesIO();Image.new('RGB',(180,240),'#8765ab').save(buf,format='PNG')
    r=client.post('/api/media',headers=headers,data={'model_id':model},
                  files={'file':(name,io.BytesIO(buf.getvalue()),'image/png')})
    assert r.status_code==201,r.text
    return r.json()['id']

def test_studio_image_private_local_and_isolated(authed):
    client,headers=authed
    first=_upload_image(client,headers,'aria')
    s=client.get('/api/media/studio/status',headers=headers)
    assert s.status_code==200 and s.json()['image_composer_ready']
    assert s.json()['ai_image_generation'] is False
    assert client.get('/api/media/studio/status').status_code==401
    req={'model_id':'aria','source_media_id':first,'format':'story',
         'headline':'O nouă poveste','subtitle':'Fashion editorial'}
    assert client.post('/api/media/studio/image',json=req).status_code==401
    r=client.post('/api/media/studio/image',headers=headers,json=req)
    assert r.status_code==201,r.text
    result=r.json(); assert result['published'] is False
    data=client.get('/api/media/'+result['id']+'/download',headers=headers).content
    assert data.startswith(b'\x89PNG')
    with Image.open(io.BytesIO(data)) as im: assert im.size==(720,1280)
    listing=client.get('/api/media',headers=headers).json()
    assert any(x['id']==result['id'] and x['origin']=='graphic' for x in listing)
    assert any(x['id']==first and x['origin']=='upload' for x in listing)
    # No cross-character media reuse.
    req['model_id']='maya'
    assert client.post('/api/media/studio/image',headers=headers,json=req).status_code==422
    # Tampered/nonexistent media IDs are rejected.
    req['model_id']='aria';req['source_media_id']='not-found'
    assert client.post('/api/media/studio/image',headers=headers,json=req).status_code==422
    events=client.get('/api/audit',headers=headers).json()
    assert any(e['action']=='media.studio.graphic' for e in events)

def test_studio_rejects_fake_png(authed):
    client,headers=authed
    fake=b'\x89PNG\r\n\x1a\n'+b'\0'*128
    r=client.post('/api/media',headers=headers,data={'model_id':'aria'},
                  files={'file':('fake.png',io.BytesIO(fake),'image/png')})
    assert r.status_code==415

def test_video_montage_local(authed):
    client,headers=authed
    first=_upload_image(client,headers,'aria')
    req={'model_id':'aria','media_ids':[first], 'format':'square','seconds_per_image':2}
    # Detects duplicate input and rejects other-model images, before FFmpeg runs.
    assert client.post('/api/media/studio/video',headers=headers,json={**req,'media_ids':[first,first]}).status_code==422
    assert client.post('/api/media/studio/video',headers=headers,json={**req,'model_id':'maya'}).status_code==422
    from vega.media_studio import ffmpeg_status
    if not ffmpeg_status()['available']:
        assert client.post('/api/media/studio/video',headers=headers,json=req).status_code==422
        return
    r=client.post('/api/media/studio/video',headers=headers,json=req)
    assert r.status_code==201,r.text
    assert r.json()['duration_seconds']==2 and r.json()['published'] is False
    media=client.get('/api/media/'+r.json()['id']+'/download',headers=headers).content
    assert len(media)>1000 and b'ftyp' in media[:20]

def test_media_schema_migrates_v02_without_deleting_data(tmp_path,monkeypatch):
    import sqlite3
    monkeypatch.setattr(store,'DATA_DIR',tmp_path)
    monkeypatch.setattr(store,'DB',tmp_path/'old.sqlite3')
    monkeypatch.setattr(store,'MEDIA_DIR',tmp_path/'media')
    con=sqlite3.connect(store.DB)
    con.execute('CREATE TABLE media (id TEXT PRIMARY KEY,filename TEXT,stored_name TEXT,mime_type TEXT,file_size INTEGER,model_id TEXT,created_at TEXT)')
    con.execute("INSERT INTO media VALUES('old','look.png','old.png','image/png',10,'aria','2026-10-01')")
    con.commit();con.close()
    store.init_db()
    with store.connect() as c:
        x=c.execute("SELECT origin FROM media WHERE id='old'").fetchone()
        assert x['origin']=='upload'
