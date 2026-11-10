"""VEGA v0.5-v0.9: private local-first editorial pipeline, analytics and integration registry.

No method in this module publishes content, stores OAuth tokens or contacts social media APIs.
"""
from __future__ import annotations

import json
import os
import re
import socket
import ipaddress
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

from . import store

PLATFORMS = ('Fanvue', 'Instagram', 'TikTok', 'X', 'Reddit')
SAFE_JSON_LIMIT = 64_000


def init_db() -> None:
    with store.connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS character_profiles (
          model_id TEXT PRIMARY KEY REFERENCES models(id),
          visual_prompt TEXT NOT NULL DEFAULT '', negative_prompt TEXT NOT NULL DEFAULT '',
          personality TEXT NOT NULL DEFAULT '', voice_profile TEXT NOT NULL DEFAULT '',
          reference_media_id TEXT REFERENCES media(id), updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS editorial_packs (
          id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES models(id),
          platform TEXT NOT NULL, topic TEXT NOT NULL, source TEXT NOT NULL,
          data_json TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft',
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS connector_registry (
          platform TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'unconfigured',
          note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS performance_daily (
          model_id TEXT NOT NULL REFERENCES models(id), platform TEXT NOT NULL,
          report_date TEXT NOT NULL, impressions INTEGER NOT NULL, clicks INTEGER NOT NULL,
          subscribers INTEGER NOT NULL, gross_cents INTEGER NOT NULL, cost_cents INTEGER NOT NULL,
          source TEXT NOT NULL, recorded_at TEXT NOT NULL,
          PRIMARY KEY(model_id,platform,report_date));
        CREATE TABLE IF NOT EXISTS delivery_preparations (
          id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES posts(id),
          post_updated_at TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
          payload_json TEXT NOT NULL);
        ''')
        for platform in PLATFORMS:
            c.execute('INSERT OR IGNORE INTO connector_registry(platform,updated_at) VALUES(?,?)',
                      (platform, store.utcnow()))


def get_model(c, model_id: str):
    m=c.execute('SELECT * FROM models WHERE id=?',(model_id,)).fetchone()
    if m is None:
        raise ValueError('Modelul nu există')
    return m


def save_character(model_id: str, data: dict, actor: str):
    with store.connect() as c:
        get_model(c,model_id)
        ref=data.get('reference_media_id') or None
        if ref:
            owned=c.execute('SELECT 1 FROM media WHERE id=? AND model_id=? AND mime_type LIKE ?',
                            (ref,model_id,'image/%')).fetchone()
            if not owned:
                raise ValueError('Referința trebuie să fie o imagine a aceluiași model')
        params=(model_id, data['visual_prompt'],data['negative_prompt'],data['personality'],
                data['voice_profile'],ref,store.utcnow())
        c.execute('''INSERT INTO character_profiles(model_id,visual_prompt,negative_prompt,personality,
                     voice_profile,reference_media_id,updated_at) VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(model_id) DO UPDATE SET visual_prompt=excluded.visual_prompt,
                     negative_prompt=excluded.negative_prompt,personality=excluded.personality,
                     voice_profile=excluded.voice_profile,reference_media_id=excluded.reference_media_id,
                     updated_at=excluded.updated_at''',params)
        store.audit(c,actor,'character.update',model_id,'identitate vizuală locală')
    return {'ok':True,'model_id':model_id,'generated':False}


def list_characters():
    with store.connect() as c:
        return [dict(row) for row in c.execute('''SELECT m.id AS model_id,m.name,m.niche,
                COALESCE(p.visual_prompt,'') AS visual_prompt,
                COALESCE(p.negative_prompt,'') AS negative_prompt,
                COALESCE(p.personality,'') AS personality,
                COALESCE(p.voice_profile,'') AS voice_profile,
                p.reference_media_id,p.updated_at FROM models m LEFT JOIN character_profiles p
                ON p.model_id=m.id ORDER BY m.rowid''')]


def safe_local_url() -> str:
    """Ollama must remain bound to loopback; never fetch an arbitrary user-supplied URL."""
    url = os.environ.get('VEGA_OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
    parsed=urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.username or parsed.password or parsed.path or parsed.query:
        raise ValueError('VEGA_OLLAMA_URL acceptă doar localhost/127.0.0.1 fără cale')
    return url


def ollama_request(endpoint: str, payload: dict | None = None, timeout: float = 8):
    url=safe_local_url()+endpoint
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    request=urllib.request.Request(url,data=data, headers={'Content-Type':'application/json'},
                                   method='POST' if data is not None else 'GET')
    # ProxyHandler({}) forbids HTTP_PROXY/HTTPS_PROXY from redirecting local request.
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError('Redirectările Ollama sunt interzise')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
    try:
        with opener.open(request,timeout=timeout) as response:
            if response.geturl() != url: raise ValueError('Redirectările Ollama sunt interzise')
            raw=response.read(SAFE_JSON_LIMIT+1)
            if len(raw)>SAFE_JSON_LIMIT: raise ValueError('Răspuns Ollama prea mare')
            return json.loads(raw)
    except (OSError,urllib.error.URLError,ValueError,json.JSONDecodeError) as exc:
        raise RuntimeError('Motorul Ollama local nu este disponibil sau răspunsul este invalid') from exc


def ollama_status():
    try:
        r=ollama_request('/api/tags',timeout=1.5)
        return {'available':True, 'models':[x.get('name','') for x in r.get('models',[]) if isinstance(x,dict)][:25],
                'endpoint':safe_local_url(),'cloud':False}
    except (RuntimeError,ValueError):
        return {'available':False,'models':[],'endpoint':'localhost only','cloud':False}


def template_pack(model, platform, topic):
    from .seo import suggest
    data=suggest(model,platform,topic)
    return {'hooks':data.get('hooks',[]),'caption':data.get('caption',''),
            'hashtags':data.get('hashtags',''),'cta':data.get('cta',''),
            'note':'Propunere offline pe șablon, nu analiză de trenduri live.'}


def create_pack(model_id: str, platform: str, topic: str, use_ollama: bool, actor: str):
    with store.connect() as c:
        model=dict(get_model(c,model_id))
        character=c.execute('SELECT * FROM character_profiles WHERE model_id=?',(model_id,)).fetchone()
    result=template_pack(model,platform,topic)
    source='template'
    if use_ollama:
        available=ollama_status()
        if not available['available'] or not available['models']:
            raise RuntimeError('Pornește Ollama și instalează un model local înainte de a solicita AI')
        model_name=os.environ.get('VEGA_OLLAMA_MODEL','') or available['models'][0]
        profile=(character['personality'] if character else model['voice'])[:400]
        prompt=(f'Scrie un text scurt de marketing pentru un personaj FICTIONAL AI adult, '
                f'nume {model["name"]}, nișa {model["niche"]}, stil {profile}. '
                f'Platforma {platform}, tema {topic}. '
                'Respectă transparența AI și politicile platformei, fără promisiuni înșelătoare. '
                'Răspunde cu JSON conținând hooks (listă de 3), caption, hashtags, cta.')
        response=ollama_request('/api/generate',{'model':model_name,'prompt':prompt,
                                                'stream':False,'format':'json'},timeout=90)
        try:
            val=json.loads(response.get('response',''))
            if not isinstance(val,dict): raise ValueError()
            result={'hooks':[str(x)[:250] for x in val.get('hooks',[])][:3],
                    'caption':str(val.get('caption',''))[:3000],
                    'hashtags':str(val.get('hashtags',''))[:400],
                    'cta':str(val.get('cta',''))[:200],
                    'note':'Draft Ollama local. Necesită verificare umană.'}
            if not result['caption'] or not result['hooks']:raise ValueError()
        except (ValueError,TypeError):
            raise RuntimeError('Răspunsul Ollama nu respectă structura JSON așteptată')
        source='ollama-local'
    pack_id=uuid.uuid4().hex
    with store.connect() as c:
        c.execute('INSERT INTO editorial_packs(id,model_id,platform,topic,source,data_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (pack_id,model_id,platform,topic,source,json.dumps(result,ensure_ascii=False),store.utcnow()))
        store.audit(c,actor,'editorial.draft',pack_id,source)
    return {'id':pack_id,'source':source,'state':'draft','output':result,'publishable':False}


def get_packs():
    with store.connect() as c:
        return [{**dict(r),'output':json.loads(r['data_json'])} for r in
                c.execute('SELECT * FROM editorial_packs ORDER BY created_at DESC LIMIT 80')]


def connector_status():
    with store.connect() as c:
        return [{'platform':r['platform'],'state':r['status'],'note':r['note'],
                 'configured':False,'publishing_enabled':False,'needs_official_api':True}
                for r in c.execute('SELECT * FROM connector_registry ORDER BY platform')]


def prepare_delivery(post_id: str, actor: str):
    """Export a *manual* delivery bundle; no outgoing HTTP traffic."""
    with store.connect() as c:
        p=c.execute('SELECT * FROM posts WHERE id=?',(post_id,)).fetchone()
        if p is None:raise ValueError('Postarea nu există')
        if p['state']!='scheduled_local' or not p['approved_at'] or not p['scheduled_for']:
            raise ValueError('Este necesară aprobarea și programarea locală')
        if c.execute("SELECT value FROM settings WHERE name='paused'").fetchone()['value']=='1':
            raise ValueError('Kill Switch este activ')
        if not p['rights_confirmed'] or not p['ai_disclosure']:
            raise ValueError('Verificarea drepturilor și etichetarea AI sunt obligatorii')
        if p['rating']=='18+' and p['platform']!='Fanvue':
            raise ValueError('Conținutul 18+ nu poate fi pregătit pentru această platformă')
        info={k:p[k] for k in ('id','model_id','platform','kind','title','hook','caption','hashtags','cta','rating','ai_disclosure','scheduled_for')}
        info['mode']='manual_export_only'
        info['disclaimer']='Nu s-a transmis nimic către platformă. Verifică regulile platformei.'
        ident=uuid.uuid4().hex
        c.execute('''INSERT INTO delivery_preparations(id,post_id,post_updated_at,status,created_at,payload_json)
                     VALUES(?,?,?,?,?,?)''', (ident,post_id,p['updated_at'],'prepared_offline',store.utcnow(),json.dumps(info,ensure_ascii=False)))
        store.audit(c,actor,'delivery.prepare',ident,'export local; fără publicare')
    return {'id':ident,'payload':info,'published':False}


def list_deliveries():
    with store.connect() as c:
        rows=c.execute('''SELECT d.*,p.updated_at AS live_updated,p.state AS live_state
                 FROM delivery_preparations d JOIN posts p ON p.id=d.post_id ORDER BY d.created_at DESC LIMIT 80''')
        return [{'id':r['id'],'post_id':r['post_id'],'status':('invalidated' if r['live_updated']!=r['post_updated_at'] or r['live_state']!='scheduled_local' else r['status']),
                 'created_at':r['created_at'],'published':False} for r in rows]


def save_metric(data:dict,actor:str):
    date=data['report_date']
    try:
        datetime.strptime(date,'%Y-%m-%d')
        if date>datetime.now(timezone.utc).date().isoformat():raise ValueError('Nu poți înregistra valori din viitor')
    except ValueError as ex:raise ValueError('Data trebuie să fie reală, YYYY-MM-DD, și să nu fie în viitor') from ex
    with store.connect() as c:
        get_model(c,data['model_id'])
        values=(data['model_id'],data['platform'],date,int(data['impressions']),int(data['clicks']),
                int(data['subscribers']),int(data['gross_cents']),int(data['cost_cents']),
                'manual',store.utcnow())
        c.execute('''INSERT INTO performance_daily(model_id,platform,report_date,impressions,clicks,
             subscribers,gross_cents,cost_cents,source,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(model_id,platform,report_date) DO UPDATE SET impressions=excluded.impressions,
             clicks=excluded.clicks, subscribers=excluded.subscribers,
             gross_cents=excluded.gross_cents,cost_cents=excluded.cost_cents,
             source=excluded.source,recorded_at=excluded.recorded_at''',values)
        store.audit(c,actor,'analytics.manual',data['model_id'],f'{date} {data["platform"]}')
    return {'saved':True,'source':'manual','currency':'USD','external_data':False}


def analytics():
    with store.connect() as c:
        rows=[dict(x) for x in c.execute('SELECT * FROM performance_daily ORDER BY report_date DESC,model_id LIMIT 500')]
    by_model={}
    for r in rows:
        m=by_model.setdefault(r['model_id'],{'model_id':r['model_id'],'impressions':0,'clicks':0,'subscribers':0,'gross_cents':0,'cost_cents':0})
        for field in ('impressions','clicks','subscribers','gross_cents','cost_cents'):m[field]+=r[field]
    totals={k:sum(r[k] for r in rows) for k in ('impressions','clicks','subscribers','gross_cents','cost_cents')}
    totals['net_cents']=totals['gross_cents']-totals['cost_cents']
    return {'data_source':'manual_only','currency':'USD','sample_size':len(rows),'totals':totals,
            'by_model':list(by_model.values()),'daily':rows,'real_time':False,
            'warning':'Date introduse manual; nu reprezintă încasări Fanvue verificate.'}
