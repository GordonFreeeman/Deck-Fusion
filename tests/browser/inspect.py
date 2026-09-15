"""Run a short actual-bundle UI inspection with simulated Steam/Decky widgets.
Requires pytest fixtures, Playwright/Chromium and locally installed JupyterLab's
React 18 chunks. Does not fetch code, run a game or simulate GPU success.
"""
import asyncio, json, re, shutil, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'py_modules'),str(ROOT)]
from conftest import installation,packages
from test_regressions_rc2 import make_plugin
from test_110 import fsr_payload
from playwright.async_api import async_playwright

async def main():
    temp=Path(tempfile.mkdtemp(prefix='fusion-inspect-'))
    e,p,root,exe=packages.__wrapped__(installation.__wrapped__(temp))
    # Synthetic DX12 game and component contents, not a real commercial game.
    from conftest import pe_bytes
    exe.write_bytes(pe_bytes(64,'dx12'));fsr_payload(e)
    e.hardware=lambda:{'has_nvidia':False,'known_non_nvidia':True,'steam_deck':True,'model':'simulated Deck inventory','devices':[]}
    plugin=make_plugin(e)
    static=Path('/opt/pyvenv/lib/python3.13/site-packages/jupyterlab/static')
    serve=temp/'web';(serve/'dist').mkdir(parents=True);shutil.copy(ROOT/'dist/index.js',serve/'dist/index.js')
    for pattern,name in [('6540.*.js','react.js'),('961.*.js','reactdom.js')]:
        source=next(static.glob(pattern));shutil.copy(source,serve/name)
    shutil.copy(ROOT/'tests/browser/host.js',serve/'host.js')
    (serve/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Deck Fusion inspection host</title>
<style> *{box-sizing:border-box}body{margin:0;background:#111923;color:#e8eef5;font:16px/1.4 Arial,sans-serif}button,input,select{font:inherit}button{padding:10px 13px;border-radius:4px;background:#334655;color:#fff;border:1px solid #526678;cursor:pointer;max-width:100%}button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,div[tabindex]:focus-visible{outline:2px solid #99d4f5;outline-offset:2px}section{margin:12px 0 22px}h2{font-size:17px;text-transform:uppercase;letter-spacing:.045em;margin:12px 0}.row{padding:9px 0;border-bottom:1px solid #ffffff12}.row button{width:100%;text-align:left}.description{font-size:13px;color:#aebdcc;padding-top:5px;line-height:1.4}.fieldline{display:flex;align-items:center;justify-content:space-between;gap:22px;min-height:36px}.fieldline label{flex:1}.fieldline input:not([type=checkbox]),select{min-width:160px;max-width:60%;color:#edf5ff;background:#263341;border:1px solid #586b7c;padding:7px;border-radius:3px}input[type=checkbox]{width:22px;height:22px;accent-color:#8ed1f3}.slider{display:flex;align-items:center;gap:12px;min-width:220px}.tabs{height:100%;display:flex;flex-direction:column;min-height:0}.tabs nav{display:flex;padding:8px 24px;gap:5px}.tabs nav button{flex:1}.tabs nav [data-active=true]{background:#527187}.tabbody{flex:1;min-height:0}.overlay{position:fixed;inset:0;background:#000a;display:flex;align-items:center;justify-content:center;padding:14px}.dialog{background:#1b2836;padding:20px 24px;border:1px solid #50667b;border-radius:8px;width:min(730px,100%);max-height:calc(100vh - 28px);overflow:auto;box-shadow:0 12px 50px #0008}.dialog>h2{margin:0;text-transform:none;font-size:21px}.dialog>p{margin:7px 0 14px;color:#b9cbda}.actions{display:flex;gap:14px;justify-content:flex-end;padding-top:18px}.actions button{min-width:130px}pre{max-width:100%}</style>
<div id="app"></div><div id="modals"></div><script src="react.js"></script><script src="reactdom.js"></script><script src="host.js"></script>''')
    out=ROOT/'evidence';out.mkdir(exist_ok=True);errors=[];result={'scope':'Actual 1.1 bundle with React18; simulated Decky controls/Steam API; real Python backend and synthetic file fixtures. No game rendering or controller hardware.'}
    async def invoke(request):
        return await getattr(plugin,request['method'])(*request['args'])
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1280,'height':800})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_default_timeout(6000)
        await page.expose_function('pycall',invoke)
        await page.set_content(re.sub(r'<script.*?</script>', '', (serve/'index.html').read_text()))
        for name in ('react.js','reactdom.js','host.js'):await page.add_script_tag(path=str(serve/name))
        await page.evaluate("source => { window.bundleURL=URL.createObjectURL(new Blob([source],{type:'text/javascript'})); }", (ROOT/'dist/index.js').read_text())
        await page.evaluate('startApp()')
        await page.get_by_text('Ready. Changes remain',exact=False).wait_for()
        await page.screenshot(path=str(out/'library-1.1-1280.png'))
        await page.get_by_role('button',name='Setup wizard',exact=True).click()
        await page.get_by_role('button',name='Next',exact=True).click()
        await page.get_by_label('Smoother motion with LSFG',exact=True).check()
        await page.get_by_label('Replace the game’s upscaler with OptiScaler',exact=True).check()
        await page.get_by_label('Add ReShade effects',exact=True).check()
        await page.get_by_role('button',name='Next',exact=True).click()
        await page.get_by_role('button',name='Use 33 → 66 / Deck 60 preset (experimental)',exact=True).click()
        await page.get_by_label('Upscaling output',exact=True).select_option('fsr4_int8')
        await page.screenshot(path=str(out/'wizard-targets-1280.png'))
        await page.set_viewport_size({'width':800,'height':500})
        await page.screenshot(path=str(out/'wizard-targets-800.png'))
        await page.get_by_role('button',name='Next',exact=True).click()
        await page.get_by_role('button',name='Next',exact=True).wait_for(state='visible')
        # Visit Tools and resume component step; readiness must be refreshed.
        await page.get_by_role('button',name='Open component tools',exact=True).click()
        await page.get_by_role('button',name='Resume wizard',exact=True).click()
        await page.get_by_role('button',name='Next',exact=True).click()
        await page.get_by_label('Curves',exact=True).check()
        await page.get_by_role('button',name='Apply this game',exact=True).click()
        modal=page.get_by_role('dialog');await modal.wait_for()
        await page.screenshot(path=str(out/'confirm-800.png'))
        await modal.get_by_role('button',name='Cancel',exact=True).click()
        assert not (exe.parent/'OptiScaler.ini').exists()
        assert not (e.store('123')/'profile.json').exists()
        assert not any(isinstance(x,dict) and x.get('steam_write') for x in await page.evaluate('calls'))
        result['cancel']='No game files, profile or Steam launch write'
        await page.set_viewport_size({'width':1280,'height':800})
        await page.get_by_role('button',name='Apply this game',exact=True).click();await modal.wait_for()
        await page.screenshot(path=str(out/'confirm-1280.png'))
        await modal.get_by_role('button',name='Accept all & apply',exact=True).click()
        await page.get_by_text('Setup complete',exact=True).wait_for(timeout=15000)
        await page.screenshot(path=str(out/'wizard-complete-1280.png'))
        applied=e.profile('123')
        assert applied['base_fps']==33 and applied['lsfg']['respect_deck_limiter']
        assert applied['opti']['fsr_mode']=='fsr4_int8' and applied['opti']['dx12']=='fsr31'
        assert (exe.parent/'OptiScaler.ini').is_file() and (exe.parent/'ReShade64.dll').is_file()
        result['apply']='Full wizard, FSR4 request, component resume, native-format confirmation, real backend journal and simulated Steam write completed'
        result['horizontal_overflow']=await page.evaluate('document.documentElement.scrollWidth>innerWidth')
        result['errors']=errors
        await browser.close()
    (out/'ui-inspection.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not errors,errors
    assert not result['horizontal_overflow']
    print(json.dumps(result,indent=2))
    shutil.rmtree(temp)
asyncio.run(main())
