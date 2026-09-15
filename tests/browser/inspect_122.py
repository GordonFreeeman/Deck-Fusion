"""Focused batch DLL, mouse controls and diagnostics UI inspection.
Real Chromium/React and Python backend; simulated Decky/Steam; no games/GPU.
"""
import asyncio, hashlib, json, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from mount import mount, BASE
sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
import conftest
from main import Plugin
from fusion_util import atomic_json, ini_read
from fusion_launch import launch_environment, parse_dll_overrides
from test_122 import input_payload, cyberpunk
OUT=BASE/'evidence/1.2.2';OUT.mkdir(exist_ok=True,parents=True)
report={'scope':'Real Chromium/React and Python; synthetic PE payloads, simulated Steam/Decky, hidden module window. No physical Steam Deck, native gamepad or GPU test.','cases':[]}

def fixture():
    folder=Path(tempfile.mkdtemp(prefix='df122-ui-'))
    e,p,root,exe=cyberpunk(conftest.packages.__wrapped__(conftest.installation.__wrapped__(folder)))
    input_payload(e)
    p['opti'].update(enabled=True,fsr_mode='fsr4_int8')
    p['reshade']['mode']='opti'
    p['base_fps']=33;p['lsfg']['multiplier']=2
    originals={name:conftest.pe_bytes()+b'TEST MOD '+name.encode() for name in ('dxgi.dll','version.dll','winmm.dll')}
    for name,content in originals.items():(exe.parent/name).write_bytes(content)
    (exe.parent/'vendor_backend.dll').write_bytes(conftest.pe_bytes()+b'NOT A LOADER')
    log=root/'red4ext/logs/red4ext.log';log.parent.mkdir(parents=True)
    log.write_text('[error] Synthetic fixture: missing plugin dependency\n')
    stored={**p,'exe':''};atomic_json(e.store('123')/'profile.json',stored)
    plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False
    return e,p,root,exe,plugin,originals

def geometry(page):
    return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]').getBoundingClientRect();const footer=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,height:f.height,bottom:f.bottom,footerTop:footer.top,scrollY,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')

loop=asyncio.new_event_loop();threading.Thread(target=loop.run_forever,daemon=True).start()
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width,height in [(1280,800),(800,500)]:
        e,p,root,exe,plugin,mods=fixture()
        page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(8000)
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        def call(request):return asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(20)
        page.expose_function('pycall',call);mount(page,fixtures={},separate=True)
        launch='WINEDLLOVERRIDES="version=n,b;other=b,n" %command% --skip-launcher'
        page.evaluate('(value)=>window.steamLaunch=value',launch)
        page.get_by_role('button',name='Open Deck Fusion',exact=True).click()
        page.get_by_text('Ready. Changes remain a draft until you select Apply settings.',exact=True).wait_for()
        page.get_by_role('button',name='DLLs',exact=True).click()
        for name in ('dxgi.dll','version.dll','winmm.dll'):
            checkbox=page.get_by_role('checkbox',name=name,exact=False)
            expect(checkbox).to_be_enabled();checkbox.check();expect(checkbox).to_be_checked()
        expect(page.get_by_role('button',name='Add selected DLLs (3)',exact=True)).to_be_enabled()
        page.get_by_role('checkbox',name='winmm.dll',exact=False).focus()
        page.screenshot(path=str(OUT/f'dll-batch-{width}x{height}.png'))
        page.get_by_role('button',name='Add selected DLLs (3)',exact=True).click()
        for module in ('dxgi','version','winmm'):
            expect(page.get_by_label(f'Load order: {module}',exact=False)).to_have_value('n,b')
        expect(page.get_by_role('button',name='Add selected DLLs (0)',exact=True)).to_be_disabled()
        # Filter finds non-common names without clearing previous custom entries.
        page.get_by_label('Filter existing DLLs',exact=False).fill('vendor_backend')
        expect(page.get_by_role('checkbox',name='vendor_backend.dll',exact=False)).to_be_visible()
        page.get_by_label('Filter existing DLLs',exact=False).fill('')
        # Diagnostics must use the unsaved, auto-selected executable.
        assert e.profile('123')['exe']==''
        page.get_by_role('button',name='Check Cyberpunk mod files and logs',exact=True).click()
        page.locator('[data-mod-diagnostics]').wait_for()
        expect(page.get_by_text('Synthetic fixture: missing plugin dependency',exact=False)).to_be_visible()
        page.locator('[data-mod-diagnostics]').evaluate('(el)=>el.scrollIntoView({block:"nearest"})')
        page.screenshot(path=str(OUT/f'mod-evidence-{width}x{height}.png'))
        card_checks=[]
        for card in page.locator('[data-df-mod-card]').all():
            card.focus()
            measure=card.evaluate('''el=>{const r=el.getBoundingClientRect(),pane=el.closest('[data-df-scroll]').getBoundingClientRect();return {key:el.dataset.dfModCard,focused:document.activeElement===el,visible:r.top>=pane.top&&r.bottom<=pane.bottom,top:r.top,bottom:r.bottom,paneBottom:pane.bottom,scrollable:el.scrollHeight>el.clientHeight}}''')
            assert measure['focused'] and measure['visible'],measure
            if measure['scrollable']:
                before=card.evaluate('(el)=>el.scrollTop');card.press('PageDown');assert card.evaluate('(el)=>el.scrollTop')>before
            card_checks.append(measure)
        page.screenshot(path=str(OUT/f'mod-card-focus-{width}x{height}.png'))
        # Input workaround modifies only the draft until the single confirmation.
        page.get_by_role('button',name='OptiScaler',exact=True).click()
        page.get_by_role('button',name='Use mouse-input compatibility settings',exact=True).click()
        expect(page.get_by_label('OptiScaler mouse input',exact=False)).to_have_value('polling')
        expect(page.get_by_label('Steam Input and other overlays',exact=False)).to_have_value('keep')
        assert not (exe.parent/'OptiScaler.ini').exists()
        page.get_by_role('button',name='Use mouse-input compatibility settings',exact=True).focus()
        page.screenshot(path=str(OUT/f'mouse-controls-{width}x{height}.png'))
        page.get_by_role('checkbox',name='Show FSR 4 verification watermark',exact=False).focus()
        page.screenshot(path=str(OUT/f'watermark-{width}x{height}.png'))
        page.get_by_role('button',name='Apply',exact=True).click()
        before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
        page.get_by_role('button',name='Apply settings',exact=True).first.click()
        page.get_by_role('button',name='Accept all & apply',exact=True).wait_for()
        g=geometry(page);assert g['moduleHeight']==0 and g['height']>=240 and g['bottom']<=g['footerTop'] and not g['horizontalOverflow'],g
        page.screenshot(path=str(OUT/f'confirmation-{width}x{height}.png'))
        page.get_by_role('button',name='Cancel',exact=True).click()
        page.get_by_role('dialog').wait_for(state='hidden')
        assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()} and page.evaluate('window.steamLaunch')==launch
        page.get_by_role('button',name='Apply settings',exact=True).first.click()
        page.get_by_role('button',name='Accept all & apply',exact=True).click()
        page.get_by_text('Applied. Restart the game to load this configuration.',exact=True).wait_for()
        ini=ini_read((exe.parent/'OptiScaler.ini').read_text())
        assert ini['FSR']['Fsr4EnableWatermark']=='auto' and ini['FSR']['Fsr4ForceEnableInt8']=='true'
        assert ini['Hotfix']['ManualInputPolling']=='true' and ini['Hotfix']['DisableOverlays']=='false'
        applied=e.profile('123')
        assert applied['base_fps']==33 and applied['lsfg']['multiplier']==2
        assert set(parse_dll_overrides(applied['wine']['custom_overrides']))=={'dxgi','version','winmm'}
        for name,content in mods.items():assert (exe.parent/name).read_bytes()==content
        runtime=json.loads((e.store('123')/'runtime.json').read_text())
        env=launch_environment(runtime,{'MLSR-WATERMARK':'1','WINEDLLOVERRIDES':'version=n,b;other=b,n'})
        assert 'MLSR-WATERMARK' not in env
        assert parse_dll_overrides(env['WINEDLLOVERRIDES'])['other']=='b,n'
        assert applied['opti']['proxy'] not in ('dxgi','version','winmm')
        assert not errors,errors
        report['cases'].append({'viewport':[width,height],'geometry':g,'batch_multiple':True,'filter_keeps_entries':True,'unsaved_draft_diagnostics':True,'mouse_pair_applied':True,'ini_watermark_auto':True,'sdk_env_absent':True,'int8_preserved':True,'original_mods_preserved':True,'cancel_readonly':True,'evidence_card_focus':card_checks,'opti_proxy':applied['opti']['proxy'],'page_errors':errors})
        page.close()
    browser.close()
loop.call_soon_threadsafe(loop.stop)
report['bundle_sha256']=hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest()
(OUT/'ui-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
