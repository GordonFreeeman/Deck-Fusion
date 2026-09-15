"""Focused repair UI inspection: real Chromium/React + Python; simulated Steam/Decky."""
import asyncio, hashlib, json, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from mount import mount, BASE
sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
import conftest
from main import Plugin
from fusion_transaction import Transaction
from test_121 import apply, files
OUT=BASE/'evidence/1.2.1';OUT.mkdir(parents=True,exist_ok=True)
report={'scope':'Real Chromium/React and Python RPC/transaction code, synthetic PE files, simulated Decky/Steam APIs. Hidden module window and visible Steam footer. No physical Deck or GPU.','cases':[]}

def fixture():
    base=Path(tempfile.mkdtemp(prefix='df121-browser-'))
    e,p,root,exe=conftest.packages.__wrapped__(conftest.installation.__wrapped__(base))
    p['opti']['enabled']=True;p['reshade']['mode']='opti';p['wine']['custom_overrides']='version=n,b'
    (exe.parent/'version.dll').write_bytes(conftest.pe_bytes()+b'EXISTING MOD')
    stage,_=apply(e,p,'WINEDLLOVERRIDES="version=n,b" %command% --skip-launcher')
    p=e.profile('123')
    # Missing tools/shaders plus one manually replaced binary.
    for rel in Transaction(root,e.store('123')).manifest()['files']:
        if not rel.endswith('.ini'):(root/rel).unlink()
    (exe.parent/'ReShade64.dll').write_bytes(b'EXTERNAL REPLACEMENT TO SNAPSHOT')
    plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False
    return e,p,root,exe,stage['launch_after'],plugin

def geometry(page):
    return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]'),foot=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,height:f?.getBoundingClientRect().height,bottom:f?.getBoundingClientRect().bottom,footerTop:foot.top,bodyScroll:scrollY,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')

def callback(plugin,loop):
    def call(request):return asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(20)
    return call

loop=asyncio.new_event_loop();thread=threading.Thread(target=loop.run_forever,daemon=True);thread.start()
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width,height in [(1280,800),(1024,640),(800,500)]:
        e,p,root,exe,launch,plugin=fixture();before=files(root);saved=(e.store('123')/'profile.json').read_bytes()
        page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(8000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.expose_function('pycall',callback(plugin,loop));mount(page,fixtures={},separate=True)
        page.evaluate('(value)=>window.steamLaunch=value',launch)
        page.get_by_role('button',name='Open Deck Fusion',exact=True).click()
        page.locator('[data-df-frame]').wait_for()
        page.get_by_role('button',name='Apply',exact=True).click()
        toggle=page.get_by_role('checkbox',name='Force repair / reinstall',exact=False)
        toggle.wait_for();assert not toggle.is_checked()
        page.get_by_role('button',name='Apply settings',exact=True).first.click()
        page.get_by_role('button',name='Review force repair',exact=True).wait_for()
        g=geometry(page)
        assert g['moduleHeight']==0 and g['height']>=240 and g['bottom']<=g['footerTop'] and not g['horizontalOverflow'],g
        page.screenshot(path=str(OUT/f'repair-blocked-{width}x{height}.png'))
        assert files(root)==before and (e.store('123')/'profile.json').read_bytes()==saved
        page.get_by_role('button',name='Review force repair',exact=True).click()
        accept=page.get_by_role('button',name='Back up & repair',exact=True);accept.wait_for()
        assert not accept.is_disabled()
        box=accept.bounding_box();assert box['y']+box['height']<g['footerTop'],box
        page.screenshot(path=str(OUT/f'repair-confirm-{width}x{height}.png'))
        items=page.locator('[data-df-review-item^="repair-"]').filter(has_not=page.get_by_text('One-time repair authorization',exact=True))
        assert page.get_by_text('Changed file: back up and replace',exact=True).count()>=1
        focus_results=[]
        for item in page.locator('[data-df-review-item^="repair-Binaries/"]').all():
            item.focus()
            measurement=item.evaluate('''el=>{const r=el.getBoundingClientRect(),c=el.closest('[data-df-review-scroll]').getBoundingClientRect();return {path:el.textContent,focused:document.activeElement===el,visible:r.top>=c.top-1&&r.bottom<=c.bottom+1,top:r.top,bottom:r.bottom,panelBottom:c.bottom}}''')
            assert measurement['focused'] and measurement['visible'],measurement
            focus_results.append(measurement)
        assert len(focus_results)>=6
        page.screenshot(path=str(OUT/f'repair-files-{width}x{height}.png'))
        page.get_by_role('button',name='Cancel',exact=True).click()
        page.get_by_role('dialog').wait_for(state='hidden')
        assert files(root)==before and (e.store('123')/'profile.json').read_bytes()==saved
        assert page.evaluate('window.steamLaunch')==launch and not toggle.is_checked()
        # Explicit one-shot switch uses the same plan and confirmation.
        toggle.check();assert toggle.is_checked()
        page.get_by_role('button',name='Apply settings',exact=True).first.click()
        page.get_by_role('button',name='Back up & repair',exact=True).click()
        page.get_by_text('Repair complete. Snapshots retained; force repair is now off. Restart the game.',exact=True).wait_for()
        assert not toggle.is_checked()
        assert not Transaction(root,e.store('123')).pending()
        for rel,meta in Transaction(root,e.store('123')).manifest()['files'].items():
            assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==meta['installed']
        assert (exe.parent/'version.dll').read_bytes().endswith(b'EXISTING MOD')
        assert e.profile('123')['wine']['custom_overrides']=='version=n,b'
        assert page.evaluate('window.steamLaunch')==launch
        receipts=list((e.store('123')/'transactions').glob('*/receipt.json'))
        repair=[json.loads(x.read_text()) for x in receipts if json.loads(x.read_text()).get('force_repair')]
        assert len(repair)==1
        assert any(x.read_bytes()==b'EXTERNAL REPLACEMENT TO SNAPSHOT' for x in (e.store('123')/'transactions'/repair[0]['token']).glob('*.before'))
        page.locator('[data-df-scroll="apply"]').evaluate('(el)=>el.scrollTop=0')
        page.screenshot(path=str(OUT/f'repair-done-{width}x{height}.png'))
        # A failed profile reload must not leave repair permission armed.
        toggle.check()
        page.evaluate('''()=>{const original=window.pycall;window.pycall=request=>{
          if(request.method==='rpc'&&request.args[0]==='profile')return Promise.resolve({ok:false,error:{message:'Simulated profile reload failure'}});
          return original(request);
        };window.restorePycall=()=>{window.pycall=original;};}''')
        page.get_by_role('button',name='Library',exact=True).click()
        page.get_by_role('button',name='Discard this draft and reload applied settings',exact=True).click()
        page.get_by_text('Simulated profile reload failure',exact=True).wait_for()
        page.evaluate('window.restorePycall()')
        page.get_by_role('button',name='Apply',exact=True).click()
        assert not toggle.is_checked()
        assert not errors,errors
        page.locator('[data-df-scroll="apply"]').evaluate('(el)=>el.scrollTop=0')
        page.screenshot(path=str(OUT/f'repair-reload-failure-{width}x{height}.png'))
        report['cases'].append({'viewport':[width,height],'geometry':g,'accept_button':box,'blocked_to_repair':True,'cancel_read_only':True,'explicit_toggle_apply':True,'toggle_reset':True,'failed_reload_disarms_repair':True,'file_focus_checks':focus_results,'reinstalled_files':len(Transaction(root,e.store('123')).manifest()['files']),'external_snapshot':True,'original_override_and_mod_preserved':True,'page_errors':errors})
        page.close()
    browser.close()
loop.call_soon_threadsafe(loop.stop)
report['bundle_sha256']=hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest()
(OUT/'ui-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
