"""Consistent SQLite + private-media backup for offline VEGA.

Backup files contain sensitive material. Never publish them to GitHub or serve via an unauthenticated URL.
Restore is an explicit offline CLI action, never an HTTP endpoint.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import store

BACKUP_LIMIT = 4 * 1024**3
MAX_FILES = 20000


def _sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def _name_safe(name: str):
    p=PurePosixPath(name)
    return bool(name) and not name.startswith('/') and '\\' not in name and '..' not in p.parts and len(p.parts)<=4


def make_backup() -> dict:
    """SQLite backup API guarantees consistent db snapshot across WAL commits."""
    backup_dir=store.DATA_DIR.parent / 'vega_private_backups'
    backup_dir.mkdir(parents=True,exist_ok=True)
    timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name=f'vega-backup-{timestamp}-{os.urandom(3).hex()}.zip'
    target=backup_dir/name
    manifest={'version':1,'created_at':store.utcnow(),'items':{},
              'includes':'SQLite database, private media; credentials as salted hashes'}
    fd,tmp=tempfile.mkstemp(prefix='vega-snapshot-',suffix='.sqlite3',dir=str(backup_dir));os.close(fd)
    partial=target.with_suffix('.partial')
    try:
        with sqlite3.connect(store.DB) as source, sqlite3.connect(tmp) as dst:
            source.backup(dst)
        count=0
        with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as out:
            db_size=Path(tmp).stat().st_size
            if db_size>BACKUP_LIMIT:raise ValueError('Baza depășește limita de backup')
            out.write(tmp,'data/vega.sqlite3')
            dig=hashlib.sha256()
            with Path(tmp).open('rb') as inp:
                while chunk:=inp.read(1024*1024):dig.update(chunk)
            manifest['items']['data/vega.sqlite3']={'sha256':dig.hexdigest(),'size':db_size}
            count+=db_size
            for path in sorted(store.MEDIA_DIR.iterdir()) if store.MEDIA_DIR.exists() else []:
                if not path.is_file() or path.is_symlink():continue
                if len(path.name)>140 or '/' in path.name:continue
                file_size=path.stat().st_size
                count+=file_size
                if count>BACKUP_LIMIT or len(manifest['items'])>=MAX_FILES:
                    raise ValueError('Backup depășește limitele locale de siguranță')
                entry='data/media/'+path.name
                digest=hashlib.sha256()
                with path.open('rb') as inp:
                    while chunk:=inp.read(1024*1024):digest.update(chunk)
                out.write(path,entry)
                manifest['items'][entry]={'sha256':digest.hexdigest(),'size':file_size}
            out.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True))
        partial.replace(target)
        return {'filename':name,'path':str(target),'bytes':target.stat().st_size,
                'files':len(manifest['items']),'sensitive':True,'public':False}
    finally:
        Path(tmp).unlink(missing_ok=True)
        partial.unlink(missing_ok=True)


def verify_backup(path: Path) -> dict:
    """Reads and checks *every* entry against manifest; no extraction."""
    path=Path(path)
    if not path.is_file():raise ValueError('Fișierul backup nu există')
    if path.stat().st_size>BACKUP_LIMIT:raise ValueError('Backup prea mare')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>MAX_FILES+1:raise ValueError('Prea multe fișiere')
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)) or any(not _name_safe(x) for x in names):
            raise ValueError('Arhivă cu căi sau intrări nesigure')
        if 'manifest.json' not in names:raise ValueError('Manifestul lipsește')
        man=json.loads(z.read('manifest.json'))
        if man.get('version')!=1 or not isinstance(man.get('items'),dict):
            raise ValueError('Versiune de backup invalidă')
        if set(names)-{'manifest.json'}!=set(man['items']):
            raise ValueError('Manifestul nu coincide cu arhiva')
        total=0
        for entry,meta in man['items'].items():
            if not (entry=='data/vega.sqlite3' or (entry.startswith('data/media/') and len(PurePosixPath(entry).parts)==3)):
                raise ValueError('Intrare necunoscută sau nesigură')
            info=z.getinfo(entry)
            total+=info.file_size
            if total>BACKUP_LIMIT:raise ValueError('Conținut decomprimat prea mare')
            dig=hashlib.sha256()
            readbytes=0
            with z.open(entry) as f:
                while chunk:=f.read(1024*1024):
                    dig.update(chunk);readbytes+=len(chunk)
            if dig.hexdigest()!=meta['sha256'] or readbytes!=meta['size']:
                raise ValueError('Integritate eșuată pentru '+entry)
        return {'valid':True,'files':len(man['items']),'bytes_uncompressed':total,
                'created_at':man['created_at'],'restore_requires_stopped_app':True}


def restore_offline(path:Path, dest:Path, confirm:bool=False):
    """Do not invoke in running server; use explicit offline command. Keeps old data untouched unless confirmed."""
    report=verify_backup(path)
    if not confirm:return {'dry_run':True,**report}
    dest=Path(dest).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise ValueError('Destinația trebuie să fie un director gol; nu suprascriem datele existente')
    dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('manifest.json'))
        for entry in manifest['items']:
            rel=PurePosixPath(entry).relative_to('data')
            outfile=dest.joinpath(*rel.parts)
            outfile.parent.mkdir(parents=True,exist_ok=True)
            with z.open(entry) as source, outfile.open('xb') as target:
                shutil.copyfileobj(source,target)
    with sqlite3.connect(dest/'vega.sqlite3') as con:
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
    if integrity!='ok':raise ValueError('SQLite restaurat nu este integru')
    return {'restored_into':str(dest),'offline_only':True,**report}
