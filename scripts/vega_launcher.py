"""Optional bundled Windows GUI-friendly launcher; not a compiled executable itself."""
from __future__ import annotations
import multiprocessing
import threading
import webbrowser


def open_app():
    try:webbrowser.open('http://127.0.0.1:8765/')
    except Exception:pass

if __name__=='__main__':
    multiprocessing.freeze_support()
    threading.Timer(2,open_app).start()
    import uvicorn
    uvicorn.run('vega.main:app',host='127.0.0.1',port=8765,log_level='warning')
