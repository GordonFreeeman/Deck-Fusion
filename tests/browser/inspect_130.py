"""Focused UI inspection: real Chromium/React/Python, simulated Decky & installer.
The Microsoft runtimes, native Steam client and GPU are not available here.
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
from test_122 import cyberpunk
from test_130 import setup_prefix, simulate_installer
OUT=BASE/'evidence/1.3.0';OUT.mkdir(exist_ok=True,parents=True)
report={'scope':'Real Chromium/React/Python. Simulated Decky/Steam and runtime installer; no physical Steam Deck, actual Microsoft installer or game/GPU result.','cases':[]}


def fixture(flatpak=False):
    directory=Path(tempfile.mkdtemp(prefix='df130-ui-'))
    e,p,root,exe=cyberpunk(conftest.packages.__wrapped__(conftest.installation.__wrapped__(directory)))
    prefix=setup_prefix(e,p)
    atomic_json(e.store('123')/'profile.json',p)
    e.prereqs.user_check=lambda:None
    e.prereqs.helper=(lambda:{'kind':'flatpak','executable':'/fixture/flatpak','available':True}) if flatpak else (lambda:{'kind':'native','executable':'/fixture/protontricks','winetricks':'/fixture/winetricks','available':True})
    e.prereqs.execute=simulate_installer(prefix)
    plugin=Plugin();plugin._engine=e;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False;plugin._runtime_cancels={}
    return e,p,root,exe,prefix,plugin


def geometry(page):
    return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]').getBoundingClientRect(),footer=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,height:f.height,bottom:f.bottom,footerTop:footer.top,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')

loop=asyncio.new_event_loop();threading.Thread(target=loop.run_forever,daemon=True).start()
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width,height in [(1280,800),(800,500)]:
        e,p,root,exe,prefix,plugin=fixture(flatpak=width==800)
        page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(10000)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def call(request):return asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(25)
        page.expose_function('pycall',call);mount(page,fixtures={},separate=True)
        launch='WINEDLLOVERRIDES="version,winmm=n,b" %command% --skip-launcher'
        page.evaluate('(value)=>window.steamLaunch=value',launch)
        # Exercise wizard entry too, then retain its draft and use the same manager.
        entry='Set up a game' if width==800 else 'Open Deck Fusion'
        page.get_by_role('button',name=entry,exact=True).click()
        page.get_by_text('Ready. Changes remain a draft until you select Apply settings.',exact=True).wait_for()
        if width==800:
            page.get_by_role('button',name='Keep draft & exit',exact=True).click()
        page.get_by_role('button',name='Runtimes',exact=True).click()
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).click()
        page.get_by_text('Prefix inspection complete. File presence does not establish successful mod loading.',exact=True).wait_for()
        expect(page.get_by_label('Proton prefix',exact=False)).to_have_value(str(prefix))
        g=geometry(page)
        page.screenshot(path=str(OUT/f'runtimes-{width}x{height}.png'))
        assert g['moduleHeight']==0 and g['bottom']<=g['footerTop'] and not g['horizontalOverflow'],g
        # Confirmation must show the actual prefix; cancelling leaves pfx byte-identical.
        before=(prefix/'user.reg').read_bytes()
        page.get_by_role('button',name='Install selected runtimes',exact=True).click()
        page.get_by_role('button',name='Back up & install',exact=True).wait_for()
        page.screenshot(path=str(OUT/f'confirm-{width}x{height}.png'))
        if width==800:
            card=page.locator('[data-runtime-confirm-card=filesystems]');card.focus()
            expect(card).to_contain_text(str(prefix.parent))
            before_scroll=card.evaluate('(el)=>el.scrollTop')
            card.press('PageDown')
            assert card.evaluate('(el)=>el.scrollTop')>before_scroll
            page.screenshot(path=str(OUT/'flatpak-grants-800x500.png'))
        button=page.get_by_role('button',name='Back up & install',exact=True)
        box=button.bounding_box();assert box['y']+box['height']<height-56
        page.get_by_role('button',name='Cancel',exact=True).click()
        page.get_by_role('dialog').wait_for(state='hidden')
        assert (prefix/'user.reg').read_bytes()==before and not (prefix.parent/'.deck-fusion-runtime-backups').exists()
        assert page.evaluate('window.steamLaunch')==launch
        # Real snapshot orchestration; the external installer is explicitly simulated.
        page.get_by_role('button',name='Install selected runtimes',exact=True).click()
        page.get_by_role('button',name='Back up & install',exact=True).click()
        page.get_by_text('Winetricks returned success and installation receipts are present.',exact=False).first.wait_for()
        page.locator('[data-runtime-receipt]').wait_for()
        expect(page.get_by_text('Result: completed',exact=True)).to_be_visible()
        for card in page.locator('[data-df-mod-card]').all():
            card.focus()
            pos=card.evaluate('(el)=>{const r=el.getBoundingClientRect();return {top:r.top,bottom:r.bottom,focused:document.activeElement===el}}')
            assert pos['focused'] and pos['bottom']<=height-56
        page.get_by_role('button',name='Restore latest runtime snapshot',exact=True).focus()
        page.screenshot(path=str(OUT/f'receipt-{width}x{height}.png'))
        page.get_by_role('button',name='Restore latest runtime snapshot',exact=True).click()
        page.get_by_role('button',name='Keep current & restore',exact=True).wait_for()
        page.screenshot(path=str(OUT/f'restore-{width}x{height}.png'))
        page.get_by_role('button',name='Cancel',exact=True).click()
        page.get_by_role('dialog').wait_for(state='hidden')
        assert page.evaluate('window.steamLaunch')==launch
        # Expose helper-failure logs without installing or downloading any app.
        (e.data/'protontricks-helper.log').write_text('SIMULATED Flatpak helper download failure')
        page.get_by_role('button',name='Check prefix and runtimes',exact=True).click()
        page.get_by_text('Prefix inspection complete. File presence does not establish successful mod loading.',exact=True).wait_for()
        page.get_by_label('Show Protontricks helper log',exact=False).check()
        page.locator('[data-df-mod-card=runtime-helper-log]').focus()
        page.screenshot(path=str(OUT/f'helper-log-{width}x{height}.png'))
        expect(page.locator('[data-df-mod-card=runtime-helper-log]')).to_contain_text('SIMULATED Flatpak helper download failure')
        assert not errors,errors
        report['cases'].append({'viewport':[width,height],'entry':entry,'helper_command_model':'flatpak' if width==800 else 'native','geometry':g,'cancel_readonly':True,'snapshot_installer_fixture':True,'restore_confirmation':True,'launch_options_unchanged':True,'errors':errors})
        page.close()
    browser.close()
loop.call_soon_threadsafe(loop.stop)
report['bundle_sha256']=hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest()
(OUT/'ui-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
