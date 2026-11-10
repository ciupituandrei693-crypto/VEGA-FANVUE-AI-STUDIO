import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException
from .store import connect, utcnow

MIN_PASSWORD = 12

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    result = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384${salt.hex()}${result.hex()}"

def check_password(password: str, stored: str) -> bool:
    try:
        algo, n, salt, digest = stored.split("$")
        if algo != "scrypt" or int(n) != 16384: return False
        trial = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=8, p=1)
        return hmac.compare_digest(trial, bytes.fromhex(digest))
    except (ValueError, TypeError): return False

def issue_token(c, username: str):
    token = secrets.token_urlsafe(40)
    expires = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    c.execute("INSERT INTO sessions(token_hash,username,expires_at) VALUES(?,?,?)",
              (hashlib.sha256(token.encode()).hexdigest(), username, expires))
    return token

def current_user(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Autentificare necesară")
    token = authorization[7:]
    if len(token) < 25:
        raise HTTPException(401, "Sesiune invalidă")
    with connect() as c:
        record = c.execute("SELECT username, expires_at FROM sessions WHERE token_hash=?",
                           (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not record or datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Sesiune expirată sau invalidă")
    return record["username"]
