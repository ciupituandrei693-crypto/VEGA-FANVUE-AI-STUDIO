from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("VEGA_DATA_DIR", str(ROOT / "local_data"))).resolve()
DB = DATA_DIR / "vega.sqlite3"
MEDIA_DIR = DATA_DIR / "media"

MODELS = [
    ("aria", "Aria Vale", "Soft luxury, eleganță și fashion", "calmă, elegantă", "rose"),
    ("maya", "Maya Solis", "Nightlife, fashion urban și glamour", "energică, sigură pe sine", "violet"),
    ("elena", "Elena Hart", "Muzică și fashion de scenă", "expresivă, creativă", "coral"),
    ("nova", "Nova Quinn", "Fashion modern și beauty", "îndrăzneață, modernă", "blue"),
    ("selene", "Selene Voss", "Luxury, beauty și wellness", "rafinată, rezervată", "gold"),
    ("claudia", "Claudia Rose", "Romantic glamour și lifestyle", "caldă, romantică", "pink"),
    ("irina", "Irina Sky", "Travel, stil și lux", "optimistă, cosmopolită", "sky"),
    ("liora", "Liora Maren", "City-chic și fashion european", "artistică, spontană", "purple"),
    ("evelyn", "Evelyn Frost", "Icy glamour, beauty și fashion", "sofisticată, minimalistă", "silver"),
]

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout=10000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def row_dict(row):
    return dict(row) if row is not None else None

def init_db():
    with connect() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
          username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES users(username),
          expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS models (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, niche TEXT NOT NULL,
          voice TEXT NOT NULL, accent TEXT NOT NULL,
          updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (
          name TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS posts (
          id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES models(id),
          platform TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
          hook TEXT NOT NULL, caption TEXT NOT NULL, hashtags TEXT NOT NULL,
          cta TEXT NOT NULL, rating TEXT NOT NULL DEFAULT 'sfw',
          ai_disclosure INTEGER NOT NULL DEFAULT 1,
          rights_confirmed INTEGER NOT NULL DEFAULT 0,
          state TEXT NOT NULL DEFAULT 'draft',
          scheduled_for TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          approved_at TEXT, rejected_reason TEXT);
        CREATE INDEX IF NOT EXISTS posts_by_model ON posts(model_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS posts_by_state ON posts(state, scheduled_for);
        CREATE TABLE IF NOT EXISTS media (
          id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_name TEXT NOT NULL,
          mime_type TEXT NOT NULL, file_size INTEGER NOT NULL,
          model_id TEXT REFERENCES models(id), created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
          entity TEXT NOT NULL, detail TEXT NOT NULL);
        """)
        for model_id, name, niche, voice, accent in MODELS:
            c.execute("INSERT OR IGNORE INTO models(id,name,niche,voice,accent,updated_at) VALUES(?,?,?,?,?,?)",
                      (model_id, name, niche, voice, accent, utcnow()))
        c.execute("INSERT OR IGNORE INTO settings(name,value) VALUES('paused','1')")

def audit(c, actor, action, entity, detail=""):
    c.execute("INSERT INTO audit(at,actor,action,entity,detail) VALUES(?,?,?,?,?)",
              (utcnow(), actor, action, entity, detail[:1000]))
