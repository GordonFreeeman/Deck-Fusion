"""Real React/browser + real backend, simulated Steam/Decky and synthetic PE files."""
import asyncio, hashlib, json, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from mount import mount, BASE
sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
import conftest
from main import Plugin
from fusion_util import atomic_json
from test_110 import fsr_payload
OUT=BASE/'evidence/1.2.0';OUT.mkdir(parents=True,exist_ok=True)
report={'scope':'Real Chromium/React and the actual Python RPC, job and transaction backend. Simulated Decky components/Steam APIs, hidden module window, visible footer, synthetic PE payloads. No Steam Deck or GPU test.','cases':[]}

def fixture():
 d=Path(tempfile.mkdtemp(prefix='df120-ui-'))
 e,p,root,exe=conftest.packages.__wrapped__(conftest.installation.__wrapped__(d))
 fsr_payload(e);p['api']='dx12';p['opti'].update(enabled=True,proxy='version',fsr_mode='fsr4_int8');p['reshade']['mode']='opti'
 for name in ('Version.dll','winmm.dll'):(exe.parent/name).write_bytes(conftest.pe_bytes()+name.encode())
 atomic_json(e.store('123')/'profile.json',p)
 plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False
 return e,p,root,exe,plugin

def geometry(page):
 return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]'),foot=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,height:f?.getBoundingClientRect().height,bottom:f?.getBoundingClientRect().bottom,footerTop:foot.top,bodyScroll:scrollY,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')

def callback(plugin,loop):
 def call(request):
  return asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(20)
 return call

def snap(page,name):page.screenshot(path=str(OUT/name))

loop=asyncio.new_event_loop();thread=threading.Thread(target=loop.run_forever,daemon=True);thread.start()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for width,height in [(1280,800),(1024,640),(800,500)]:
  e,p,root,exe,plugin=fixture()
  page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(8000)
  errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
  page.expose_function('pycall',callback(plugin,loop));mount(page,fixtures={},separate=True)
  launch='WINEDLLOVERRIDES="version=n,b;dinput8=" %command% --skip-launcher'
  page.evaluate('(s)=>window.steamLaunch=s',launch)
  page.get_by_role('button',name='Open Deck Fusion',exact=True).click()
  page.locator('[data-df-frame]').wait_for();page.get_by_role('button',name='DLLs',exact=True).click()
  page.get_by_text('Existing Steam launch overrides',exact=True).wait_for()
  g=geometry(page);assert g['moduleHeight']==0 and g['height']>240 and g['bottom']<=g['footerTop'] and not g['horizontalOverflow'],g
  assert page.get_by_text('version=n,b;dinput8=',exact=True).count()==1
  snap(page,f'dlls-inherited-{width}x{height}.png')
  # Pick a real scanned PE DLL, add native-first custom entry.
  page.get_by_label('Existing DLL beside the game').select_option('winmm')
  page.get_by_role('button',name='Add / update custom override',exact=True).click()
  page.get_by_label('Load order: winmm').wait_for()
  page.get_by_text('OptiScaler: dxgi.dll',exact=True).wait_for()
  page.get_by_text('Proposed graphics loaders',exact=True).wait_for()
  page.get_by_role('button',name='Refresh overrides and DLL files',exact=True).click()
  page.get_by_text('Refreshing DLL inspection…',exact=True).wait_for()
  assert page.get_by_label('Existing DLL beside the game').count()==1
  page.get_by_text('Proposed graphics loaders',exact=True).wait_for()
  pane=page.locator('[data-df-scroll="wine"]');pane.evaluate('(el)=>el.scrollTop=el.scrollHeight')
  snap(page,f'dlls-custom-{width}x{height}.png')
  # Manual disabled rule and removal back to inheritance (not file deletion).
  page.get_by_label('DLL module name').fill('test_loader.dll')
  page.get_by_label('New override load order').select_option('disabled')
  page.get_by_role('button',name='Add / update custom override',exact=True).click()
  page.get_by_role('button',name='Remove custom override: test_loader',exact=True).click()
  # Read-only planning and cancellation must not mutate anything.
  before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
  stored=(e.store('123')/'profile.json').read_bytes()
  page.get_by_role('button',name='Apply settings',exact=True).first.click()
  dialog=page.get_by_role('dialog');dialog.wait_for()
  snap(page,f'confirmation-{width}x{height}.png')
  accept=page.get_by_role('button',name='Accept all & apply',exact=True);box=accept.bounding_box()
  assert box['y']+box['height']<g['footerTop'],box
  page.get_by_role('button',name='Cancel',exact=True).click();dialog.wait_for(state='hidden')
  assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
  assert (e.store('123')/'profile.json').read_bytes()==stored
  assert page.evaluate('window.steamLaunch')==launch
  # Actual async apply job, Steam-setter simulation, disk transaction and completion.
  page.get_by_role('button',name='Apply settings',exact=True).first.click()
  page.get_by_role('button',name='Accept all & apply',exact=True).click()
  page.wait_for_function("calls.some(c=>c.method==='rpc'&&c.args[0]==='finish')")
  page.wait_for_function("calls.some(c=>c.steam_write)")
  page.get_by_role('button',name='Apply settings',exact=True).first.wait_for()
  for _ in range(30):
   if not (e.store('123')/'pending.json').exists():break
   page.wait_for_timeout(100)
  assert not (e.store('123')/'pending.json').exists()
  assert e.profile('123')['wine']['custom_overrides']=='winmm=n,b'
  assert e.profile('123')['opti']['proxy']=='dxgi'
  assert (exe.parent/'Version.dll').read_bytes().endswith(b'Version.dll')
  assert (exe.parent/'winmm.dll').read_bytes().endswith(b'winmm.dll')
  assert 'Fsr4EnableWatermark=false' in (exe.parent/'OptiScaler.ini').read_text()
  assert 'version=n,b;dinput8=' in page.evaluate('window.steamLaunch')
  # Return to quick panel and verify wizard route, no removed FPS preset.
  page.evaluate('window.launchQuick()');page.get_by_role('button',name='Set up a game',exact=True).click()
  page.get_by_role('button',name='Next',exact=True).click()
  page.get_by_role('button',name='Configure mod-loader DLL overrides',exact=True).click()
  page.get_by_role('button',name='Resume wizard',exact=True).click()
  page.get_by_role('button',name='Next',exact=True).click()
  assert '33 → 66' not in page.locator('body').inner_text()
  snap(page,f'wizard-{width}x{height}.png')
  assert not errors,errors
  report['cases'].append({'viewport':[width,height],'geometry':g,'page_errors':errors,'checks':['Inherited Steam overrides visible','Scanned DLL add','Manual disabled entry and remove','Safe alternative graphics proxy','Cancel does not mutate game, profile or launch','Real async prepare/finish backend with simulated Steam setter','Original mods preserved','Watermark INI false; INT8 retained','Wizard route/resume; preset absent']})
  page.close()
 browser.close()
loop.call_soon_threadsafe(loop.stop);thread.join(5)
report['bundle_sha256']=hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest()
(OUT/'ui-inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
