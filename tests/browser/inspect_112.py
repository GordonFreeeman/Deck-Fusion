import json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from mount import mount,BASE
out=BASE/'evidence/1.1.2';out.mkdir(parents=True,exist_ok=True)
records=[]

def geometry(page):
 return page.evaluate('''()=>{const f=document.querySelector('[data-df-frame]')||document.querySelector('[data-df-recovery]');const footer=document.querySelector('#footer').getBoundingClientRect();return {moduleHeight:host.moduleWindow.innerHeight,ownerHeight:f?.ownerDocument.defaultView.innerHeight,height:f?.getBoundingClientRect().height,bottom:f?.getBoundingClientRect().bottom,footerTop:footer.top,bodyScroll:window.scrollY,horizontalOverflow:document.documentElement.scrollWidth>innerWidth}}''')
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for width,height in [(1280,800),(1024,640),(800,500)]:
  for action in ['Open Deck Fusion','Set up a game']:
   page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(4000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   mount(page,separate=True);page.get_by_role('button',name=action,exact=True).click();page.wait_for_function("document.querySelector('[data-df-frame]')?.style.height.endsWith('px')")
   page.wait_for_timeout(100);initial=geometry(page)
   assert initial['moduleHeight']==0 and initial['height']>240,initial
   assert initial['bottom']<=initial['footerTop'] and not initial['horizontalOverflow'],initial
   if action=='Open Deck Fusion':
    for tab in ['Library','LSFG','OptiScaler','ReShade','Apply','Tools']:
     page.get_by_role('button',name=tab,exact=True).click();pane=page.locator('[data-df-scroll]').first
     pane.evaluate('(node)=>{node.scrollTop=node.scrollHeight}')
    page.get_by_role('button',name='Library',exact=True).click()
   else:
    next_button=page.get_by_role('button',name='Next',exact=True);box=next_button.bounding_box();assert box['y']+box['height']<initial['footerTop']
    assert next_button.evaluate('(n)=>{const r=n.getBoundingClientRect();return n.contains(n.ownerDocument.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}')
    # Focus a clipped control in the content pane. Only the inner pane may scroll.
    page.get_by_role('button',name='More library options',exact=True).evaluate('(n)=>n.focus({preventScroll:true})')
    assert page.evaluate('window.scrollY')==0
    next_button.click();page.get_by_role('button',name='Back',exact=True).click()
   screenshot=('wizard' if action=='Set up a game' else 'manager')+f'-{width}x{height}.png'
   page.screenshot(path=str(out/screenshot))
   mutations=page.evaluate("calls.filter(c=>c.method==='start_job'||(c.method==='rpc'&&!['state','profile','scan','schema','requirements','wine_context'].includes(c.args[0])))")
   assert not mutations,mutations
   assert not errors,errors
   records.append({'case':action,'viewport':[width,height],'geometry':initial,'unexpected_calls':mutations,'page_errors':errors,'screenshot':screenshot})
   page.close()
 # Owner resize, absent observer, then recovery from a broken native component.
 page=browser.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(4000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 mount(page,separate=True)
 page.evaluate("Object.defineProperty(window,'ResizeObserver',{configurable:true,value:class{constructor(){throw Error('simulated unavailable observer')}}})")
 page.get_by_role('button',name='Open Deck Fusion',exact=True).click();page.wait_for_timeout(150)
 assert geometry(page)['height']>600
 page.set_viewport_size({'width':800,'height':500});page.wait_for_timeout(150);resized=geometry(page);assert resized['height']==388,resized
 # Retry loads a new manager and does not reset/persist/apply a game profile.
 page.evaluate("window.breakTabs=true;host.moduleWindow.DFL.Navigation.Navigate('/deck-fusion/setup')")
 page.get_by_role('button',name='Keep draft & exit',exact=True).click()
 page.get_by_text('Deck Fusion could not open this screen',exact=True).wait_for()
 recovery=geometry(page);assert recovery['bottom']<recovery['footerTop'],recovery
 page.screenshot(path=str(out/'recovery-800x500.png'))
 page.evaluate('window.breakTabs=false');page.get_by_role('button',name='Retry opening',exact=True).click()
 page.locator('[data-df-frame]').wait_for();page.wait_for_timeout(80);assert geometry(page)['height']==388
 page.evaluate("window.breakTabs=true;host.moduleWindow.DFL.Navigation.Navigate('/deck-fusion/setup')")
 page.get_by_role('button',name='Keep draft & exit',exact=True).click()
 page.get_by_role('button',name='Back to Steam',exact=True).click();page.get_by_text('Steam Library',exact=True).wait_for()
 assert not errors,errors
 mutations=page.evaluate("calls.filter(c=>c.method==='start_job'||(c.method==='rpc'&&!['state','profile','scan','schema','requirements','wine_context'].includes(c.args[0])))");assert not mutations
 records.append({'case':'owner resize / observer unavailable / route failure / retry / return to Steam','resized':resized,'recovery':recovery,'page_errors':errors,'unexpected_calls':mutations,'expected_caught_error':'Simulated native Tabs render failure'})
 browser.close()
report={'scope':'Real Chromium and React 19.1.1; simulated Decky components, Steam API, session storage and read-only backend responses generated with Python fixtures. Two distinct browser Windows. Not native Decky or a physical Steam Deck.','bundle_sha256':hashlib.sha256((BASE/'dist/index.js').read_bytes()).hexdigest(),'cases':records}
(out/'ui-inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
