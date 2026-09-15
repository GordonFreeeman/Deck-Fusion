"""General-game workflow inspection. Real React/Chromium/Python, simulated Decky.
No Steam Deck, Protontricks, Microsoft installer or graphics device is simulated as real.
"""
import asyncio
import hashlib
import json
import sys
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from mount import mount, BASE
sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
import conftest
from main import Plugin
from fusion_util import atomic_json
from test_130 import setup_prefix
from test_131 import add_game, fake_execute
OUT=BASE/'evidence/1.3.1';OUT.mkdir(exist_ok=True,parents=True)
report={'scope':'Real Chromium/React/Python, synthetic games and simulated Decky/Steam/installer. No physical Steam Deck or real runtime installation.', 'cases':[]}


def fixture():
    directory=Path(tempfile.mkdtemp(prefix='df131-ui-'))
    e,p,root,exe=conftest.packages.__wrapped__(conftest.installation.__wrapped__(directory))
    prefix=setup_prefix(e,p)
    other,_,other_exe=add_game(e,'456','Zeta Windows Game');other_prefix=setup_prefix(e,other)
    native,nroot,nexe=add_game(e,'789','Zulu Native Game');nexe.unlink()
    native_exe=nroot/'native';native_exe.write_bytes(b'\x7fELF\x02'+b'\0'*128);native_exe.chmod(0o755);native['exe']=str(native_exe)
    for profile in (p,other,native):atomic_json(e.store(profile['appid'])/'profile.json',profile)
    (exe.parent/'OptiScaler.log').write_text('INFO synthetic game log\nERROR fixture historical message\n')
    e.prereqs.user_check=lambda:None
    e.prereqs.helper=lambda:{'kind':'native','executable':'/fixture/protontricks','winetricks':'/fixture/winetricks','available':True}
    calls=[]
    e.prereqs.execute=fake_execute({'appid':'123','prefix':str(prefix)},calls)
    plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False;plugin._runtime_cancels={}
    return e,p,exe,prefix,other_prefix,plugin,calls


def geometry(page):
    return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]').getBoundingClientRect(),footer=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,height:f.height,bottom:f.bottom,footerTop:footer.top,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')


loop=asyncio.new_event_loop();threading.Thread(target=loop.run_forever,daemon=True).start()
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width,height in [(1280,800),(1024,640),(800,500)]:
        e,p,exe,prefix,other_prefix,plugin,calls=fixture()
        page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(10000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def call(request):return asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(25)
        page.expose_function('pycall',call);mount(page,fixtures={},separate=True)
        launch='WINEDLLOVERRIDES="version,winmm=n,b" %command% --skip-launcher'
        page.evaluate('(value)=>window.steamLaunch=value',launch)
        entry='Set up a game' if width==800 else 'Open Deck Fusion'
        page.get_by_role('button',name=entry,exact=True).click()
        page.get_by_text('Ready. Changes remain a draft until you select Apply settings.',exact=True).wait_for()
        wizard_resume=False
        if width==800:
            page.get_by_role('button',name='Next',exact=True).click()
            page.get_by_role('button',name='Optional Windows runtime setup',exact=True).click()
            page.get_by_role('button',name='Resume wizard',exact=True).click()
            expect(page.get_by_text('Step 2 of 5 · Choose features',exact=True)).to_be_visible()
            wizard_resume=True
            page.get_by_role('button',name='Optional Windows runtime setup',exact=True).click()
        else:
            page.get_by_role('button',name='Open runtime setup',exact=True).click()
        expect(page.get_by_text('Windows runtimes',exact=True)).to_be_visible()
        assert 'Cyberpunk' not in page.locator('[data-df-frame]').inner_text()
        expect(page.get_by_label('d3dcompiler_47',exact=False)).not_to_be_checked()
        expect(page.get_by_label('vcrun2022',exact=False)).not_to_be_checked()
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).click()
        page.get_by_text('Prefix inspection complete. File presence does not establish successful game or mod loading.',exact=True).wait_for()
        expect(page.get_by_label('Proton prefix',exact=False)).to_have_value(str(prefix))
        expect(page.get_by_role('button',name='Install selected runtimes',exact=True)).to_be_disabled()
        page.get_by_label('d3dcompiler_47',exact=False).check();page.get_by_label('vcrun2022',exact=False).check()
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).focus()
        g=geometry(page);page.screenshot(path=str(OUT/f'runtimes-{width}x{height}.png'))
        assert g['moduleHeight']==0 and g['bottom']<=g['footerTop'] and not g['horizontalOverflow'],g
        before=(prefix/'user.reg').read_bytes()
        page.get_by_role('button',name='Install selected runtimes',exact=True).click()
        expect(page.get_by_role('dialog')).to_contain_text('Install selected Windows runtimes?')
        expect(page.get_by_role('dialog')).to_contain_text('Test Game · App ID 123')
        expect(page.get_by_role('dialog')).to_contain_text(str(prefix))
        page.screenshot(path=str(OUT/f'confirm-{width}x{height}.png'))
        button=page.get_by_role('button',name='Back up & install',exact=True)
        box=button.bounding_box();assert box['y']+box['height']<height-56
        page.get_by_role('button',name='Cancel',exact=True).click();page.get_by_role('dialog').wait_for(state='hidden')
        assert (prefix/'user.reg').read_bytes()==before and not calls
        assert not (prefix.parent/'.deck-fusion-runtime-backups').exists()
        # Install orchestration once. The external installer is an explicit fixture.
        if width==1280:
            page.get_by_role('button',name='Install selected runtimes',exact=True).click()
            page.get_by_role('button',name='Back up & install',exact=True).click()
            page.get_by_text('Result: completed',exact=True).wait_for()
            assert calls==['d3dcompiler_47','vcrun2022']
        # General diagnostics are available without a Cyberpunk-named executable.
        page.get_by_role('button',name='DLLs',exact=True).click()
        page.get_by_role('button',name='Check game files and logs',exact=True).click()
        page.get_by_text('Game file inventory loaded. No files or settings were changed.',exact=True).wait_for()
        expect(page.locator('[data-mod-diagnostics]')).to_contain_text('Graphics configuration')
        assert page.get_by_role('button',name='Check Cyberpunk mod files and logs',exact=True).count()==0
        page.locator('[data-df-mod-card="Graphics configuration"]').focus()
        page.screenshot(path=str(OUT/f'diagnostics-{width}x{height}.png'))
        page.get_by_role('button',name='Open runtime setup',exact=True).click()
        expect(page.get_by_text('Windows runtimes',exact=True)).to_be_visible()
        # A new game must not inherit an approved prefix, checked recipes or receipt.
        page.get_by_role('button',name='Library',exact=True).click()
        page.get_by_label('Installed game',exact=False).select_option('456')
        page.get_by_text('Ready. Changes remain a draft until you select Apply settings.',exact=True).wait_for()
        page.get_by_role('button',name='Open runtime setup',exact=True).click()
        expect(page.get_by_label('d3dcompiler_47',exact=False)).not_to_be_checked()
        expect(page.get_by_label('vcrun2022',exact=False)).not_to_be_checked()
        assert page.locator('[data-runtime-receipt]').count()==0
        assert str(prefix) not in page.locator('[data-df-frame]').inner_text()
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).click()
        page.get_by_text('Prefix inspection complete. File presence does not establish successful game or mod loading.',exact=True).wait_for()
        expect(page.get_by_label('Proton prefix',exact=False)).to_have_value(str(other_prefix))
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).focus()
        page.screenshot(path=str(OUT/f'second-game-{width}x{height}.png'))
        # Native Linux case is explained and cannot run a Windows installer.
        page.get_by_role('button',name='Library',exact=True).click()
        page.get_by_label('Installed game',exact=False).select_option('789')
        page.get_by_text('Ready. Changes remain a draft until you select Apply settings.',exact=True).wait_for()
        page.get_by_role('button',name='Open runtime setup',exact=True).click()
        assert page.get_by_role('button',name='Check prefix and runtimes',exact=True).count()==0
        assert page.get_by_role('button',name='Install selected runtimes',exact=True).count()==0
        assert page.get_by_label('d3dcompiler_47',exact=False).count()==0
        expect(page.get_by_role('button',name='Choose a Windows executable',exact=True)).to_be_visible()
        expect(page.get_by_text('This is a native Linux executable.',exact=False)).to_be_visible()
        page.screenshot(path=str(OUT/f'native-{width}x{height}.png'))
        native_box=page.get_by_text('This is a native Linux executable.',exact=False).bounding_box()
        assert native_box['y']>=0 and native_box['y']+native_box['height']<=height-56
        native_action=page.get_by_role('button',name='Choose a Windows executable',exact=True)
        native_action.focus()
        action_box=native_action.bounding_box()
        assert action_box['y']>=0 and action_box['y']+action_box['height']<=height-56
        page.screenshot(path=str(OUT/f'native-action-{width}x{height}.png'))
        assert page.evaluate('window.steamLaunch')==launch and not errors,errors
        report['cases'].append({'viewport':[width,height],'entry':entry,'geometry':g,'wizard_resume':wizard_resume,'cancel_readonly':True,'general_diagnostics':True,'game_switch_resets_runtime_state':True,'native_blocked':True,'simulated_installer_calls':calls,'launch_options_unchanged':True,'errors':errors})
        page.close()
    browser.close()
loop.call_soon_threadsafe(loop.stop)
report['bundle_sha256']=hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest()
(OUT/'ui-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
