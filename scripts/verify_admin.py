"""LAN must never allow first-user setup from the iPhone."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vega import store

store.init_db()
with store.connect() as conn:
    exists=conn.execute('SELECT 1 FROM users LIMIT 1').fetchone()
if not exists:
    print('STOP: configurează administratorul prin START_VEGA_WINDOWS.bat înainte de accesul pe iPhone')
    raise SystemExit(1)
print('Administrator local confirmat. Conexiunea LAN cere autentificare.')
