"""Synthetic game installation for v2 browser verification. Never touches real games."""
import asyncio, sys, tempfile, threading
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
import conftest
from main import Plugin
from fusion_util import atomic_json
from test_130 import setup_prefix

def fixture():
 directory=Path(tempfile.mkdtemp(prefix='df20-ui-'))
 e,p,root,exe=conftest.packages.__wrapped__(conftest.installation.__wrapped__(directory))
 p['name']='Cyberpunk 2077';p['base_fps']=30;p['lsfg'].update(enabled=True,multiplier=2)
 # Synthetic PE files and local package placeholders, no proprietary game data.
 steam=e.home/'.local/share/Steam/steamapps'
 (steam/'appmanifest_123.acf').write_text('"AppState" { "appid" "123" "name" "Cyberpunk 2077" "installdir" "Test Game" }')
 atomic_json(e.store('123')/'profile.json',p)
 setup_prefix(e,p)
 e.prereqs.user_check=lambda:None
 e.prereqs.helper=lambda:{'kind':'native','executable':'/fixture/protontricks','winetricks':'/fixture/winetricks','available':True}
 plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False;plugin._runtime_cancels={}
 return e,p,plugin
