"""VEGA Universal v0.2 — authenticated local-first API; NO real publishing."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import store
from .security import MIN_PASSWORD, check_password, current_user, hash_password, issue_token
from .seo import suggest

PLATFORMS = ("Instagram", "TikTok", "X", "Reddit", "Fanvue")
KINDS = ("photo", "video", "story", "carousel", "text")
WEB = store.ROOT / "web"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    yield

app = FastAPI(title="VEGA Universal API", version="0.2.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")

@app.middleware("http")
async def secure_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "public, max-age=120"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
        "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return response

@app.get("/")
def index():
    return FileResponse(WEB / "index.html", media_type="text/html")

@app.get("/health")
def health():
    return {"service":"vega", "version":"0.2.0", "mode":"local-only", "external_connections":False}

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=1, max_length=200)

# Per-process, local-only login throttling (not intended for public Internet exposure).
LOGIN_FAILURES: dict[str, list[float]] = {}

@app.get("/api/setup-state")
def setup_state():
    with store.connect() as c:
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"configured":bool(count), "local_only":True}

@app.post("/api/setup", status_code=201)
def setup(payload: Credentials, request: Request):
    # First-admin creation is permitted only from this PC, never from another device.
    client_ip = request.client.host if request.client else ""
    if client_ip not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403,"Configurarea inițială este permisă doar local")
    if len(payload.password) < MIN_PASSWORD:
        raise HTTPException(422, f"Parola trebuie să aibă cel puțin {MIN_PASSWORD} caractere")
    with store.connect() as c:
        if c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            raise HTTPException(409,"Administratorul este deja configurat")
        c.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                  (payload.username,hash_password(payload.password),store.utcnow()))
        token = issue_token(c,payload.username)
        store.audit(c,payload.username,"account.setup","user", "administrator local creat")
    return {"token":token, "username":payload.username}

@app.post("/api/login")
def login(payload: Credentials, request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [t for t in LOGIN_FAILURES.get(ip,[]) if now-t < 300]
    LOGIN_FAILURES[ip] = recent
    if len(recent) >= 8:
        raise HTTPException(429, "Prea multe încercări. Revino în câteva minute")
    with store.connect() as c:
        user = c.execute("SELECT username,password_hash FROM users WHERE username=?", (payload.username,)).fetchone()
        if not user or not check_password(payload.password,user["password_hash"]):
            recent.append(now)
            raise HTTPException(401, "Utilizator sau parolă incorectă")
        LOGIN_FAILURES.pop(ip,None)
        c.execute("DELETE FROM sessions WHERE expires_at < ?",(store.utcnow(),))
        token = issue_token(c,user["username"])
        store.audit(c,user["username"],"account.login","session")
        return {"token":token, "username":user["username"]}

@app.post("/api/logout")
def logout(user: str = Depends(current_user), authorization: str = Header(default="")):
    with store.connect() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?",
                  (hashlib.sha256(authorization[7:].encode()).hexdigest(),))
        store.audit(c,user,"account.logout","session")
    return {"ok":True}

@app.get("/api/me")
def me(user: str = Depends(current_user)):
    return {"username":user, "role":"owner", "mode":"supravegheat", "external_connections":False}

@app.get("/api/models")
def models(user: str = Depends(current_user)):
    with store.connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM models ORDER BY CASE id " +
                " ".join(f"WHEN '{m[0]}' THEN {i}" for i,m in enumerate(store.MODELS)) + " END")]

class ModelUpdate(BaseModel):
    niche: str = Field(min_length=3,max_length=160)
    voice: str = Field(min_length=3,max_length=100)

@app.put("/api/models/{model_id}")
def update_model(model_id: str, payload: ModelUpdate, user: str = Depends(current_user)):
    with store.connect() as c:
        result = c.execute("UPDATE models SET niche=?,voice=?,updated_at=? WHERE id=?",
                           (payload.niche,payload.voice,store.utcnow(),model_id))
        if not result.rowcount: raise HTTPException(404,"Modelul nu există")
        store.audit(c,user,"model.update",model_id)
    return {"ok":True}

class SeoRequest(BaseModel):
    model_id: str
    platform: Literal["Instagram","TikTok","X","Reddit","Fanvue"]
    topic: str = Field(min_length=3,max_length=180)

@app.post("/api/seo/suggest")
def seo(payload: SeoRequest, user: str = Depends(current_user)):
    with store.connect() as c:
        model = c.execute("SELECT * FROM models WHERE id=?",(payload.model_id,)).fetchone()
    if not model: raise HTTPException(404,"Modelul nu există")
    return suggest(model,payload.platform,payload.topic)

class PostInput(BaseModel):
    model_id: str
    platform: Literal["Instagram","TikTok","X","Reddit","Fanvue"]
    kind: Literal["photo","video","story","carousel","text"] = "photo"
    title: str = Field(min_length=3,max_length=150)
    hook: str = Field(default="",max_length=300)
    caption: str = Field(min_length=3,max_length=5000)
    hashtags: str = Field(default="",max_length=600)
    cta: str = Field(default="",max_length=500)
    rating: Literal["sfw","18+"] = "sfw"
    ai_disclosure: bool = True
    rights_confirmed: bool = False

    @field_validator("title","caption")
    @classmethod
    def no_empty_string(cls,v):
        if not v.strip(): raise ValueError("Câmp obligatoriu")
        return v.strip()


def validate_post(p: PostInput):
    if p.rating == "18+" and p.platform != "Fanvue":
        raise HTTPException(422,"Materialele 18+ sunt organizate doar pentru Fanvue")
    if not p.ai_disclosure:
        raise HTTPException(422,"Etichetarea transparentă a personajului AI este obligatorie")

@app.post("/api/posts", status_code=201)
def create_post(payload: PostInput, user: str = Depends(current_user)):
    validate_post(payload)
    pid = uuid.uuid4().hex
    t = store.utcnow()
    with store.connect() as c:
        if not c.execute("SELECT 1 FROM models WHERE id=?",(payload.model_id,)).fetchone():
            raise HTTPException(404,"Modelul nu există")
        c.execute("""INSERT INTO posts (id,model_id,platform,kind,title,hook,caption,hashtags,cta,rating,
          ai_disclosure,rights_confirmed,state,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (pid,payload.model_id,payload.platform,payload.kind,payload.title,payload.hook,payload.caption,
                   payload.hashtags,payload.cta,payload.rating,int(payload.ai_disclosure),int(payload.rights_confirmed),
                   "draft",t,t))
        store.audit(c,user,"post.create",pid,f"{payload.model_id}/{payload.platform}")
    return {"id":pid,"state":"draft"}

@app.get("/api/posts")
def list_posts(model_id: str|None = None, state: str|None = None, user: str = Depends(current_user)):
    sql = "SELECT p.*,m.name AS model_name FROM posts p JOIN models m ON p.model_id=m.id WHERE 1=1"
    params=[]
    if model_id: sql += " AND model_id=?";params.append(model_id)
    if state: sql += " AND state=?";params.append(state)
    sql += " ORDER BY p.created_at DESC LIMIT 500"
    with store.connect() as c:
        return [dict(r) for r in c.execute(sql,params)]

@app.put("/api/posts/{post_id}")
def edit_post(post_id: str, payload: PostInput, user: str = Depends(current_user)):
    validate_post(payload)
    with store.connect() as c:
        post = c.execute("SELECT * FROM posts WHERE id=?",(post_id,)).fetchone()
        if not post: raise HTTPException(404,"Postarea nu există")
        if not c.execute("SELECT 1 FROM models WHERE id=?",(payload.model_id,)).fetchone():
            raise HTTPException(404,"Modelul nu există")
        c.execute("""UPDATE posts SET model_id=?,platform=?,kind=?,title=?,hook=?,caption=?,hashtags=?,cta=?,
            rating=?,ai_disclosure=?,rights_confirmed=?,state='draft',approved_at=NULL,scheduled_for=NULL,
            rejected_reason=NULL,updated_at=? WHERE id=?""",
            (payload.model_id,payload.platform,payload.kind,payload.title,payload.hook,payload.caption,
             payload.hashtags,payload.cta,payload.rating,int(payload.ai_disclosure),int(payload.rights_confirmed),
             store.utcnow(),post_id))
        store.audit(c,user,"post.edit_approval_revoked",post_id)
    return {"ok":True,"state":"draft","approval_revoked":True}


def get_post(c,post_id):
    post=c.execute("SELECT * FROM posts WHERE id=?",(post_id,)).fetchone()
    if not post: raise HTTPException(404,"Postarea nu există")
    return post

def is_paused(c):
    return c.execute("SELECT value FROM settings WHERE name='paused'").fetchone()[0]=="1"

@app.post("/api/posts/{post_id}/submit")
def submit_post(post_id: str,user: str=Depends(current_user)):
    with store.connect() as c:
        p=get_post(c,post_id)
        if p["state"]!="draft": raise HTTPException(409,"Doar schițele pot fi trimise spre aprobare")
        c.execute("UPDATE posts SET state='in_review',updated_at=? WHERE id=?",(store.utcnow(),post_id))
        store.audit(c,user,"post.submit",post_id)
    return {"state":"in_review"}

@app.post("/api/posts/{post_id}/approve")
def approve_post(post_id: str,user: str=Depends(current_user)):
    with store.connect() as c:
        p=get_post(c,post_id)
        if is_paused(c): raise HTTPException(423,"Kill Switch este activ. Dezactivează-l înainte de aprobare")
        if p["state"]!="in_review": raise HTTPException(409,"Postarea trebuie să fie în verificare")
        if not p["rights_confirmed"]: raise HTTPException(422,"Confirmă drepturile de utilizare înainte de aprobare")
        if not p["ai_disclosure"]: raise HTTPException(422,"Etichetarea AI este obligatorie")
        c.execute("UPDATE posts SET state='approved',approved_at=?,updated_at=? WHERE id=?",
                  (store.utcnow(),store.utcnow(),post_id))
        store.audit(c,user,"post.approve",post_id)
    return {"state":"approved"}

class Rejection(BaseModel):
    reason: str=Field(min_length=3,max_length=500)

@app.post("/api/posts/{post_id}/reject")
def reject_post(post_id: str,payload: Rejection,user: str=Depends(current_user)):
    with store.connect() as c:
        p=get_post(c,post_id)
        if p["state"]!="in_review": raise HTTPException(409,"Postarea nu este în verificare")
        c.execute("UPDATE posts SET state='draft',rejected_reason=?,updated_at=? WHERE id=?",
                  (payload.reason,store.utcnow(),post_id))
        store.audit(c,user,"post.reject",post_id,payload.reason)
    return {"state":"draft"}

class ScheduleRequest(BaseModel):
    scheduled_for: str

@app.post("/api/posts/{post_id}/schedule")
def schedule_post(post_id: str,payload: ScheduleRequest,user: str=Depends(current_user)):
    try:
        dt = datetime.fromisoformat(payload.scheduled_for.replace("Z","+00:00"))
        if not dt.tzinfo or dt.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValueError("data nevalidă sau în trecut")
    except ValueError:
        raise HTTPException(422,"Folosește o dată viitoare cu fus orar")
    with store.connect() as c:
        p=get_post(c,post_id)
        if is_paused(c): raise HTTPException(423,"Kill Switch activ")
        if p["state"]!="approved": raise HTTPException(409,"Postarea trebuie aprobată înainte de programare")
        c.execute("UPDATE posts SET state='scheduled_local',scheduled_for=?,updated_at=? WHERE id=?",
                  (dt.astimezone(timezone.utc).isoformat(),store.utcnow(),post_id))
        store.audit(c,user,"post.schedule_local",post_id,dt.isoformat())
    return {"state":"scheduled_local", "published":False}

@app.post("/api/posts/{post_id}/unschedule")
def unschedule(post_id: str,user: str=Depends(current_user)):
    with store.connect() as c:
        p=get_post(c,post_id)
        if p["state"]!="scheduled_local": raise HTTPException(409,"Postarea nu este programată")
        c.execute("UPDATE posts SET state='approved',scheduled_for=NULL,updated_at=? WHERE id=?",
                  (store.utcnow(),post_id))
        store.audit(c,user,"post.unschedule",post_id)
    return {"state":"approved"}

@app.get("/api/settings")
def get_settings(user: str=Depends(current_user)):
    with store.connect() as c:
        return {"paused":is_paused(c),"publisher_enabled":False,
                "server_external":False,"gpu_cloud":False,"social_accounts_connected":0}

class SettingsInput(BaseModel):
    paused: bool

@app.put("/api/settings")
def update_settings(payload: SettingsInput,user: str=Depends(current_user)):
    with store.connect() as c:
        c.execute("UPDATE settings SET value=? WHERE name='paused'",("1" if payload.paused else "0",))
        store.audit(c,user,"killswitch.pause" if payload.paused else "killswitch.resume","system")
    return {"paused":payload.paused,"publisher_enabled":False}

@app.get("/api/dashboard")
def dashboard(user: str=Depends(current_user)):
    with store.connect() as c:
        counts={r["state"]:r["n"] for r in c.execute("SELECT state,COUNT(*) AS n FROM posts GROUP BY state")}
        posts_total=sum(counts.values())
        items=[dict(r) for r in c.execute("""SELECT p.id,p.title,p.platform,p.state,p.scheduled_for,m.name AS model_name
          FROM posts p JOIN models m ON m.id=p.model_id WHERE p.state='scheduled_local'
          ORDER BY p.scheduled_for ASC LIMIT 5""")]
        events=[dict(r) for r in c.execute("SELECT at,action,entity,detail FROM audit ORDER BY id DESC LIMIT 7")]
        files=c.execute("SELECT COUNT(*) FROM media").fetchone()[0]
        return {"models":len(store.MODELS),"posts":posts_total,"review":counts.get("in_review",0),
                "approved":counts.get("approved",0),"scheduled":counts.get("scheduled_local",0),
                "media":files,"paused":is_paused(c),"upcoming":items,"events":events,
                "revenue_available":False,"social_accounts_connected":0}

@app.get("/api/audit")
def audit_events(user: str=Depends(current_user)):
    with store.connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 80")]

@app.get("/api/media")
def list_media(user: str=Depends(current_user)):
    with store.connect() as c:
        return [dict(r) for r in c.execute("SELECT id,filename,mime_type,file_size,model_id,created_at FROM media ORDER BY created_at DESC LIMIT 300")]

@app.post("/api/media",status_code=201)
async def upload_media(file:UploadFile=File(...),model_id:str=Form(...),user:str=Depends(current_user)):
    if model_id not in {m[0] for m in store.MODELS}: raise HTTPException(404,"Modelul nu există")
    allowed={"image/jpeg":(".jpg",".jpeg"),"image/png":(".png",),
             "image/webp":(".webp",),"video/mp4":(".mp4",)}
    filename=Path(file.filename or "media").name[:120]
    content_type=(file.content_type or "").lower()
    suffix=Path(filename).suffix.lower()
    if content_type not in allowed or suffix not in allowed[content_type]:
        raise HTTPException(415,"Acceptăm doar JPEG, PNG, WebP și MP4")
    target_id=uuid.uuid4().hex
    destination=store.MEDIA_DIR/(target_id+suffix)
    size=0
    header=b""
    limit=50*1024*1024
    try:
        with destination.open("wb") as out:
            while True:
                chunk=await file.read(1024*1024)
                if not chunk:break
                if not header:header=chunk[:24]
                size+=len(chunk)
                if size>limit:raise HTTPException(413,"Fișierul depășește 50 MB")
                out.write(chunk)
        valid=(content_type=="image/jpeg" and header.startswith(b"\xff\xd8\xff")) or \
              (content_type=="image/png" and header.startswith(b"\x89PNG\r\n\x1a\n")) or \
              (content_type=="image/webp" and header.startswith(b"RIFF") and b"WEBP" in header[8:16]) or \
              (content_type=="video/mp4" and len(header)>12 and header[4:8]==b"ftyp")
        if not valid:raise HTTPException(415,"Conținutul fișierului nu corespunde formatului declarat")
        with store.connect() as c:
            c.execute("INSERT INTO media(id,filename,stored_name,mime_type,file_size,model_id,created_at) VALUES(?,?,?,?,?,?,?)",
                      (target_id,filename,destination.name,content_type,size,model_id,store.utcnow()))
            store.audit(c,user,"media.upload",target_id,filename)
        return {"id":target_id,"filename":filename,"size":size}
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

@app.get("/api/media/{media_id}/download")
def download_media(media_id:str,user:str=Depends(current_user)):
    with store.connect() as c:
        record=c.execute("SELECT * FROM media WHERE id=?",(media_id,)).fetchone()
    if not record:raise HTTPException(404,"Fișierul nu există")
    path=store.MEDIA_DIR/record["stored_name"]
    if not path.is_file():raise HTTPException(404,"Fișierul lipsește de pe disc")
    return FileResponse(path,media_type=record["mime_type"],filename=record["filename"])

@app.get("/api/export")
def export_approved(user:str=Depends(current_user)):
    # Export is a local preparation artifact; never triggers remote posting.
    with store.connect() as c:
        items=[dict(r) for r in c.execute("SELECT * FROM posts WHERE state IN ('approved','scheduled_local') ORDER BY created_at DESC")]
        store.audit(c,user,"posts.export_local","export",str(len(items)))
    return {"format":"VEGA_LOCAL_EXPORT_0.2", "published":False,
            "platform_connections":False,"exported_at":store.utcnow(),"posts":items}
