/* Real React and jsdom, with explicitly mocked layout metrics and Steam/Decky.
 * This suite does NOT constitute browser rendering or physical hardware testing.
 * npm ci
 * node --test tests/studio-dom.test.mjs
 * DF_TEST_MODULES can select a separate test-only node_modules directory.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const localModules=new URL('../node_modules/',import.meta.url).pathname;
const modules=process.env.DF_TEST_MODULES||(fs.existsSync(path.join(localModules,'jsdom'))?localModules:null);
const skip=!modules?'Install test dependencies with npm ci, or set DF_TEST_MODULES':false;
const source=fs.readFileSync(new URL('../dist/index.js',import.meta.url),'utf8').replace('export default function(){','window.__makePlugin=function(){');
let JSDOM,React,ReactDOM;
if(modules){const req=createRequire(path.resolve(modules,'package.json'));({JSDOM}=req('jsdom'));const bootstrap=new JSDOM('<!doctype html><body></body>');global.window=bootstrap.window;global.document=bootstrap.window.document;Object.defineProperty(global,'navigator',{value:bootstrap.window.navigator,configurable:true});React=req('react');ReactDOM=req('react-dom/client');}
const settle=async(ms=15)=>{await new Promise(r=>setTimeout(r,ms));};
async function host({width=1280,height=800,raw=true,native=false,rdna2Fix=false,guided=false,prepare=null,nativeScroll=false,initialLaunch='--skip-launcher'}={}){
 const dom=new JSDOM('<!doctype html><div id="root"></div><div id="modal"></div>',{url:'https://deck-fusion.test',pretendToBeVisual:true,runScripts:'outside-only'}),w=dom.window;
 global.window=w;global.document=w.document;Object.defineProperty(global,'navigator',{value:w.navigator,configurable:true});
 Object.defineProperty(w,'innerWidth',{value:width,writable:true});Object.defineProperty(w,'innerHeight',{value:height,writable:true});w.document.hasFocus=()=>true;
 // Deliberately synthetic geometry: verifies algorithms, never screenshots.
 Object.defineProperties(w.HTMLElement.prototype,{clientWidth:{configurable:true,get(){return this.classList.contains('df-reader')?Math.min(600,w.innerWidth-90):w.innerWidth;}},clientHeight:{configurable:true,get(){if(this.classList.contains('df-options'))return Math.max(44,w.innerHeight-290);return this.classList.contains('df-reader')?Math.max(70,w.innerHeight-370):w.innerHeight-112;}},offsetWidth:{configurable:true,get(){return this.clientWidth;}},offsetHeight:{configurable:true,get(){return this.clientHeight;}},scrollHeight:{configurable:true,get(){if(this.classList.contains('df-reader'))return Math.max(this.clientHeight,(this.textContent||'').split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(line.length/(this.clientWidth/8))),0)*22+26);return this.clientHeight;}}});
 w.HTMLElement.prototype.getBoundingClientRect=function(){return {x:0,y:40,left:0,top:40,right:this.clientWidth,bottom:40+this.clientHeight,width:this.clientWidth,height:this.clientHeight};};
 let hit=null;w.document.elementFromPoint=()=>hit||w.document.querySelector('[data-df-studio]');
 const h=React.createElement,routes=new Map(),calls=[],listeners=[],rawState={callback:null,unregistered:false,nativeCalls:[]},routeLog=[];
 const root=ReactDOM.createRoot(w.document.querySelector('#root')),modal=ReactDOM.createRoot(w.document.querySelector('#modal'));
 const fields={
  PanelSection:({title,children})=>h('section',null,h('h3',null,title),children),PanelSectionRow:({children})=>h('div',null,children),
  ButtonItem:({children,onClick,disabled})=>h('button',{onClick,disabled},children),DialogButton:({children,...props})=>h('button',props,children),
  ToggleField:()=>null,TextField:()=>null,DropdownItem:()=>null,SliderField:()=>null,
  Focusable:React.forwardRef(({children,onActivate,onCancel,onButtonDown,focusClassName,focusWithinClassName,...props},ref)=>h('div',{...props,ref:el=>{if(el){el.__activate=onActivate;el.__cancel=onCancel;el.__button=onButtonDown;}if(typeof ref==='function')ref(el);else if(ref)ref.current=el;}},children)),
  ConfirmModal:p=>h('div',{role:'dialog'},h('h2',null,p.strTitle),p.children,h('button',{onClick:p.onCancel},'Cancel'),h('button',{disabled:p.bOKDisabled,onClick:p.onOK},p.strOKButtonText)),
  showModal(element){const close=()=>modal.render(null);modal.render(React.cloneElement(element,{closeModal:close}));return {Close:close};},
  Navigation:{Navigate:to=>{routeLog.push(to);const Route=routes.get(to);root.render(Route?h(Route):h('div',null,'Steam Library'));},CloseSideMenus(){}},staticClasses:{}
 };
 const scrollBridge={element:null,direction:null};
 if(nativeScroll){
  fields.ScrollPanel=React.forwardRef(({children,scrollDirection,...props},ref)=>h('div',{...props,ref:el=>{scrollBridge.element=el;scrollBridge.direction=scrollDirection;if(typeof ref==='function')ref(el);else if(ref)ref.current=el;}},children));
  fields.ScrollPanelGroup=({children})=>h(React.Fragment,null,children);
 }
 const profile={schema:4,appid:'123',name:'Cyberpunk 2077',root:'/games/Cyberpunk',exe:'/games/Cyberpunk/bin/x64/Cyberpunk2077.exe',api:'dx12',base_fps:30,lsfg:{enabled:true,multiplier:2,flow_scale:.75,performance_mode:true,allow_fp16:true,respect_deck_limiter:false,override_present_mode:false,preserve_swapchain_image_count:false},opti:{fsr4_rdna2_fix:rdna2Fix,enabled:false,proxy:'dxgi',dx11:'auto',dx12:'auto',vulkan:'auto',spoof:'auto',fg:false,fsr_mode:'auto',fsr4_watermark:false,mouse_input:'auto',steam_input:'auto',overrides:{}},reshade:{mode:'off',proxy:'auto',performance:true,overlay_key:36,packs:[],techniques:[],uniforms:{},raw_preset:'',raw_config:''},wine:{custom_overrides:''},setup:{version:0,runtimes:[],runtime_prefix:''}};
 const fixtures={state:{games:[{appid:'123',name:profile.name,root:profile.root}],packages:{},legacy_layers:[],settings:{include_shortcuts:false},bundled:{},hardware:{}},profile,scan:{candidates:[{path:profile.exe,relative:'bin/x64/Cyberpunk2077.exe',bits:64,api:'dx12',kind:'pe'}],warnings:[]},schema:{opti:[],shaders:[],packs:[]},wine_context:{files:[],prefixes:[],registry:[]},requirements:{items:[],needs_registration:false}};
 let activeJob=null;const jobResults={runtime_status:{prefix:'/compat/123/pfx',prefixes:['/compat/123/pfx'],helper:{available:true},runtimes:[],blockers:[]}};
 fixtures.launch_cleanup=({launch})=>({before:launch,cleaned:launch,after:launch,removed:[],warnings:[]});
 if(prepare)prepare({fixtures,profile,fields,jobResults});
 const api={routerHook:{addRoute:(r,f)=>routes.set(r,f),removeRoute:r=>routes.delete(r)},call:async(method,...args)=>{calls.push({method,args});if(method==='rpc')return {ok:true,result:structuredClone(typeof fixtures[args[0]]==='function'?fixtures[args[0]](args[1]):fixtures[args[0]]||{})};if(method==='active_jobs')return {ok:true,result:[]};if(method==='start_job'){activeJob={action:args[0],payload:args[1]};return {ok:true,result:{id:'test-job'}};}if(method==='get_job'){const handler=jobResults[activeJob.action];const result=typeof handler==='function'?await handler(activeJob.payload):handler||{profile:activeJob.payload.profile||profile,approval_token:'test-approval',blockers:[],changes:[],warnings:[],launch_after:'%command% --skip-launcher',resolutions:[]};return {ok:true,result:{state:'done',result}};}throw Error(method);}};
 let liveLaunch=initialLaunch;
 Object.assign(w,{SP_REACT:React,DFL:fields,SteamClient:{Apps:{RegisterForAppDetails:(id,cb)=>{listeners.push(cb);cb({strLaunchOptions:liveLaunch});return {unregister(){}};},SetAppLaunchOptions:(id,value)=>{liveLaunch=value;listeners.forEach(cb=>cb({strLaunchOptions:value}));}},Input:{...(raw?{RegisterForControllerStateChanges:cb=>{rawState.callback=cb;return {unregister:()=>{rawState.callback=null;rawState.unregistered=true;}}}}:{}),...(native?{SetWebBrowserActionset:enabled=>rawState.nativeCalls.push(enabled)}:{})}},__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit:{connect:()=>api}});
 w.eval(source+'\nwindow.__studio={studioInventory,useMeasuredPages,StudioReviewContent,StudioOverlay,StudioButton,StudioField,SetupStudio,EffectPicker,setupEffects,setupSteps,startupGame,sameGuidedGraphicsPlan};');
 const plugin=w.__makePlugin();root.render(plugin.content);await settle();fields.Navigation.Navigate(guided?'/deck-fusion':'/deck-fusion/expert');await settle(280);
 const el=(label)=>[...w.document.querySelectorAll('[data-df-focus],button')].find(e=>e.getAttribute('aria-label')===label||e.textContent===label);
 const click=async label=>{const e=el(label);assert.ok(e,`Missing ${label}`);e.click();await settle();return e;};
 const key=async(name,target=w.document.activeElement)=>{target.dispatchEvent(new w.KeyboardEvent('keydown',{key:name,bubbles:true,cancelable:true}));await settle();};
 const close=async()=>{root.unmount();modal.unmount();await settle();w.close();};
 return {w,root,modal,fields,fixtures,calls,rawState,routeLog,jobResults,scrollBridge,el,click,key,close,setHit:e=>hit=e};
}
test('all tabs and every settings page retain controls, labels, and keyboard page focus',{skip},async()=>{
 const t=await host();try{
  for(const name of ['Library','Motion','Upscaling','ReShade','DLLs','Runtimes','Apply','Tools']){
   await t.click(name);let count=0;do{const cards=[...t.w.document.querySelectorAll('[data-df-card]')];assert.ok(cards.length<=4);for(const card of cards){assert.ok(card.textContent.trim());assert.ok(card.querySelector('[data-df-focus]'));}count++;if(t.el('Next settings page').getAttribute('aria-disabled')==='true')break;cards[0].querySelector('[data-df-focus]').focus();await t.key('PageDown');assert.ok(t.w.document.querySelector('[data-df-studio]').contains(t.w.document.activeElement),'Pagination kept keyboard focus');assert.ok(count<30,'Pagination terminates');}while(true);
  }
 }finally{await t.close();}
});
test('mouse toggle, slider keyboard adjustment, selection, text save and draft preservation',{skip},async()=>{
 const t=await host();try{
  await t.click('Motion');const toggle=t.w.document.querySelector('[role=switch]');assert.equal(toggle.getAttribute('aria-checked'),'true');toggle.click();await settle();assert.equal(t.w.document.querySelector('[role=switch]').getAttribute('aria-checked'),'false');
  const adjust=t.el('Adjust Frame multiplier');adjust.focus();await t.key('ArrowRight',adjust);assert.equal(t.w.document.querySelector('input[aria-label="Frame multiplier"]').value,'3');
  await t.click('Library');await t.click('Edit Find a game');let input=t.w.document.querySelector('[data-df-overlay] input');const set=Object.getOwnPropertyDescriptor(t.w.HTMLInputElement.prototype,'value').set;set.call(input,'Cyber');input.dispatchEvent(new t.w.Event('input',{bubbles:true}));input.dispatchEvent(new t.w.Event('change',{bubbles:true}));await settle();await t.click('Save to draft');
  assert.equal(t.w.document.querySelector('[data-df-card="Find a game"] .df-card-action').textContent,'Cyber');await t.click('Rendering API: DirectX 12');await t.click('DirectX 11');assert.ok(t.el('Rendering API: DirectX 11'));
  await t.click('Motion');assert.equal(t.w.document.querySelector('[role=switch]').getAttribute('aria-checked'),'false');assert.equal(t.w.document.querySelector('input[aria-label="Frame multiplier"]').value,'3');
  const drafts=JSON.parse(t.w.sessionStorage.getItem('deck-fusion-drafts'));assert.equal(drafts['123'].lsfg.multiplier,3);
  assert.equal(t.calls.filter(x=>x.method==='start_job').length,0,'Draft edits cannot install files');
 }finally{await t.close();}
});
test('raw R3 after idle clicks owned modal, refuses foreign overlay, and cleans subscription',{skip},async()=>{
 const t=await host();try{
  let clicks=0;const target=t.w.document.createElement('button');target.textContent='Owned cancel';target.onclick=()=>clicks++;
  const dialog=t.w.document.createElement('div');dialog.setAttribute('role','dialog');dialog.innerHTML='<div data-df-owned-dialog></div>';dialog.appendChild(target);t.w.document.body.appendChild(dialog);t.setHit(target);
  t.rawState.callback([{unControllerIndex:0,ulButtons:0,sRightStickX:12000,sRightStickY:0}]);await settle(320);
  t.rawState.callback([{unControllerIndex:0,ulButtons:1<<26,sRightStickX:0,sRightStickY:0}]);assert.equal(clicks,1,'R3 reacquires ownership after idle and reaches owned modal');
  t.rawState.callback([{unControllerIndex:0,ulButtons:1<<26,sRightStickX:0,sRightStickY:0}]);assert.equal(clicks,1,'Held click does not repeat');
  const foreign=t.w.document.createElement('button');foreign.onclick=()=>clicks++;t.w.document.body.appendChild(foreign);t.setHit(foreign);
  t.rawState.callback([{unControllerIndex:0,ulButtons:0}]);t.rawState.callback([{unControllerIndex:0,ulButtons:1<<18}]);assert.equal(clicks,1,'Foreign UI cannot be activated');
 }finally{await t.close();assert.equal(t.rawState.unregistered,true);assert.equal(t.rawState.callback,null);}
});
test('measured reader preserves newline-rich diagnostics across pages and resize',{skip},async()=>{
 const t=await host({height:500});try{
  const payload=Array.from({length:100},(_,i)=>`${i}`).join('\n')+'\nEND';let ref={current:null};
  function Reader(){const chunks=t.w.__studio.useMeasuredPages(payload,ref);return React.createElement('div',null,React.createElement('div',{className:'df-reader',ref},chunks[0]),React.createElement('output',{'data-pages':true},JSON.stringify(chunks)));}
  t.root.render(React.createElement(Reader));await settle(50);let chunks=JSON.parse(t.w.document.querySelector('output').textContent);assert.ok(chunks.length>1);assert.equal(chunks.join(''),payload);const small=chunks.length;
  t.w.innerHeight=1000;t.w.dispatchEvent(new t.w.Event('resize'));await settle(50);chunks=JSON.parse(t.w.document.querySelector('output').textContent);assert.equal(chunks.join(''),payload);
  assert.ok(chunks.length<small,'A taller reader holds more lines per page');
 }finally{await t.close();}
});
test('compact and narrow mode paginate two controls; missing raw API stays usable',{skip},async()=>{
 for(const viewport of [{width:800,height:500},{width:390,height:844}]){const t=await host({...viewport,raw:false});try{assert.ok(t.w.document.querySelectorAll('[data-df-card]').length<=2);assert.ok(t.el('Next settings page'));await t.click('Next settings page');assert.ok(t.w.document.querySelector('[data-df-studio]'));}finally{await t.close();}}
});

test('RDNA2 installation toggle is prechecked from profile, can be cleared, and stays cleared across tabs',{skip},async()=>{
 const t=await host({rdna2Fix:true});try{
  await t.click('Upscaling');const label='Install RDNA2 ghosting fix (FSR 4.1.1b)';let steps=0;
  while(!t.el(label)){await t.click('Next settings page');assert.ok(++steps<20);}
  assert.equal(t.el(label).getAttribute('aria-checked'),'true');await t.click(label);assert.equal(t.el(label).getAttribute('aria-checked'),'false');
  await t.click('Library');await t.click('Upscaling');assert.equal(t.el(label).getAttribute('aria-checked'),'false');
  assert.equal(JSON.parse(t.w.sessionStorage.getItem('deck-fusion-drafts'))['123'].opti.fsr4_rdna2_fix,false);
  assert.equal(t.calls.filter(x=>x.method==='start_job').length,0,'Unchecking never installs or applies anything');
 }finally{await t.close();}
});

test('tab headings are plain names and exit returns to Steam Home',{skip},async()=>{
 const t=await host();try{
  for(const name of ['Library','Motion','Upscaling','ReShade','DLLs','Runtimes','Apply','Tools']){await t.click(name);assert.equal(t.w.document.querySelector('.df-hero h1').textContent,name);assert.equal(t.w.document.querySelector('.df-hero p'),null);}
  await t.click('Back to Steam');assert.equal(t.routeLog.at(-1),'/library/home');
 }finally{await t.close();}
});
test('native mouse mode preserves clicks, avoids duplicate raw input, suspends outside Studio, and releases on exit',{skip},async()=>{
 const t=await host({native:true});try{
  assert.deepEqual(t.rawState.nativeCalls,[true]);assert.equal(typeof t.rawState.callback,'function');
  let unexpected=0;const fake=t.w.document.createElement('button');fake.onclick=()=>unexpected++;t.w.document.querySelector('[data-df-studio]').appendChild(fake);t.setHit(fake);
  t.rawState.callback([{unControllerIndex:0,ulButtons:1<<26,sRightStickX:0,sRightStickY:0}]);assert.equal(unexpected,0,'Native mode never synthesizes duplicate raw clicks');
  await t.click('Motion');t.w.document.querySelector('[role=switch]').click();await settle();
  assert.equal(t.w.document.querySelector('[role=switch]').getAttribute('aria-checked'),'false');
  const external=t.w.document.createElement('button');external.textContent='Steam menu';t.w.document.body.appendChild(external);external.focus();await settle();assert.equal(t.rawState.nativeCalls.at(-1),false);
  t.el('Library').focus();await settle();assert.equal(t.rawState.nativeCalls.at(-1),true);
  t.w.dispatchEvent(new t.w.Event('blur'));assert.equal(t.rawState.nativeCalls.at(-1),false);
  t.w.dispatchEvent(new t.w.Event('focus'));assert.equal(t.rawState.nativeCalls.at(-1),true);
  await t.key('Escape',t.el('Library'));assert.equal(t.routeLog.at(-1),'/library/home');await settle();assert.equal(t.rawState.nativeCalls.at(-1),false);
 }finally{await t.close();assert.equal(t.rawState.nativeCalls.at(-1),false);}
});
test('game and shader pickers use measured compact rows and retain every option through resize',{skip},async()=>{
 const t=await host();try{
  for(const title of ['Installed game','ReShade shader']){
   const options=Array.from({length:23},(_,i)=>({data:i,label:`${title} ${i+1}`}));let chosen=null;
   t.root.render(React.createElement('div',{className:'df-studio'},React.createElement(t.w.__studio.StudioOverlay,{key:title,model:{type:'select',title,options,value:0,choose:x=>chosen=x.data},close(){},short:false,narrow:false,pageRef:{current:null}})));await settle(50);
   assert.equal(t.w.document.querySelectorAll('.df-option').length,10,'510 mock CSS pixels fit ten 44px rows plus 6px gaps');
   const seen=[];for(let page=0;page<3;page++){seen.push(...[...t.w.document.querySelectorAll('.df-option span')].map(e=>e.textContent));if(page<2)await t.click('Next');}
   assert.deepEqual(seen,options.map(x=>x.label));
   t.w.innerHeight=600;t.w.dispatchEvent(new t.w.Event('resize'));await settle(50);
   assert.equal(t.w.document.querySelectorAll('.df-option').length,6);assert.ok(t.w.document.querySelector('[data-df-overlay]').contains(t.w.document.activeElement));
   t.w.document.querySelector('.df-option').click();await settle();assert.ok(Number.isInteger(chosen));
   t.w.innerHeight=800;t.w.dispatchEvent(new t.w.Event('resize'));await settle();
  }
 }finally{await t.close();}
});


const setupStep=t=>t.w.document.querySelector('[data-setup-step]')?.dataset.setupStep;
const draft=t=>JSON.parse(t.w.sessionStorage.getItem('deck-fusion-drafts'))['123'];
const jobs=t=>t.calls.filter(x=>x.method==='start_job').map(x=>x.args[0]);
async function go(t,expected){await t.click('Next');await settle(35);assert.equal(setupStep(t),expected);}
async function reachReview(t,allowBlocked=false){
 for(let n=0;n<12&&setupStep(t)!=='review';n++){
  if(t.el('Close effects'))await t.click('Done');
  await t.click('Next');await settle(25);
 }
 assert.equal(setupStep(t),'review');if(!allowBlocked)assert.notEqual(t.el('Apply this game').getAttribute('aria-disabled'),'true',t.w.document.querySelector('.df-setup-alert')?.textContent);
}
function runtimeFixtures({fixtures,profile,jobResults}){
 let installed=false;
 const status=()=>({prefix:'/compat/123/pfx',prefixes:['/compat/123/pfx'],helper:{available:false},blockers:[],runtimes:[{name:'d3dcompiler_47',recorded:installed},{name:'vcrun2022',recorded:installed}]});
 jobResults.runtime_status=status;
 jobResults.runtime_helper_plan={approval:'helper-token'};
 jobResults.runtime_plan={approval:'runtime-token'};
 jobResults.runtime_install=()=>{installed=true;return {state:'completed'};};
 jobResults.plan=payload=>({profile:payload.profile,approval_token:installed?'after-runtime':'before-runtime',blockers:[],warnings:[],resolutions:[],changes:[],dll_context:{registry:installed?[{name:'d3dcompiler_47'}]:[]},dll_summary:{effective:installed?'d3dcompiler_47=n,b':'',opti:'off',reshade:'off'},launch_after:'%command% --skip-launcher'});
 jobResults.prepare=payload=>{Object.assign(profile,payload.profile);return {token:'graphics-token',launch_after:'%command% --skip-launcher'};};
 fixtures.finish={committed:true};
}
test('guided DLL injection keeps manual selection and chains ReShade through OptiScaler',{skip},async()=>{
 const t=await host({guided:true});try{
  await go(t,'target');await go(t,'features');await t.click('OptiScaler');await t.click('ReShade');await go(t,'injection');
  assert.match(t.w.document.querySelector('.df-setup-body').textContent,/ReShade64.dll/);
  t.w.document.querySelector('[data-df-card="OptiScaler DLL"] .df-card-action').click();await settle();await t.click('version.dll');
  assert.equal(draft(t).opti.proxy,'version');assert.equal(draft(t).wine.opti_proxy_manual,true);
  await t.click('Back');await go(t,'injection');
  assert.match(t.w.document.querySelector('.df-setup-body').textContent,/version=n,b/);
  assert.equal(jobs(t).includes('prepare'),false);
  await reachReview(t);assert.match(t.w.document.querySelector('.df-setup-summary').textContent,/OptiScaler: version.dll/);
 }finally{await t.close();}
});
test('standalone ReShade offers graphics DLL names and keeps explicit selection',{skip},async()=>{
 const t=await host({guided:true});try{
  await go(t,'target');await go(t,'features');await t.click('ReShade');await go(t,'injection');
  assert.equal(t.w.document.querySelector('[data-df-card="OptiScaler DLL"]'),null);
  t.w.document.querySelector('[data-df-card="ReShade DLL"] .df-card-action').click();await settle();
  assert.ok(t.el('dxgi.dll'));assert.equal(t.el('version.dll'),undefined);await t.click('d3d12.dll');
  assert.equal(draft(t).reshade.proxy,'d3d12');assert.equal(draft(t).wine.reshade_proxy_manual,true);
 }finally{await t.close();}
});
test('native VC evidence skips installer even without a Winetricks receipt',{skip},async()=>{
 const t=await host({guided:true,prepare:ctx=>{runtimeFixtures(ctx);ctx.profile.setup={version:1,runtimes:['vcrun2022'],runtime_prefix:''};ctx.jobResults.runtime_status=()=>({prefix:'/compat/123/pfx',prefixes:['/compat/123/pfx'],helper:{available:true},blockers:[],runtimes:[{name:'vcrun2022',recorded:false,satisfied:true}]});}});
 try{await reachReview(t);await t.click('Apply this game');await settle(80);assert.equal(jobs(t).includes('runtime_install'),false);assert.ok(jobs(t).includes('prepare'));}
 finally{await t.close();}
});
test('stale runtime receipt cannot override failed DLL verification',{skip},async()=>{
 const t=await host({guided:true,prepare:ctx=>{runtimeFixtures(ctx);ctx.profile.setup={version:1,runtimes:['vcrun2022'],runtime_prefix:''};ctx.jobResults.runtime_status=()=>({prefix:'/compat/123/pfx',prefixes:['/compat/123/pfx'],helper:{available:true},blockers:[],runtimes:[{name:'vcrun2022',recorded:true,satisfied:false}]});}});
 try{await reachReview(t);await t.click('Apply this game');await settle(80);assert.ok(jobs(t).includes('runtime_install'));assert.equal(jobs(t).includes('prepare'),false);}
 finally{await t.close();}
});
test('guided setup uses each Next stage, routes ReShade automatically, and keeps the draft',{skip},async()=>{
 const downloaded=[];
 const t=await host({guided:true,rdna2Fix:true,prepare:({fixtures,jobResults})=>{
  fixtures.schema.packs=[{id:'standard',name:'Standard'},{id:'extra',name:'Extra'}];
  jobResults.shader=({id})=>{downloaded.push(id);fixtures.state.packages.shaders??={};fixtures.state.packages.shaders[id]={path:'/cache/'+id};fixtures.schema.shaders.push({file:id+'.fx',relative:id+'.fx',uniforms:[],pack:id,techniques:[id]});return {};};
 }});
 try{
  assert.equal(setupStep(t),'game');assert.equal(t.w.document.querySelector('.df-nav'),null);
  assert.equal(t.el('Optional Windows runtime setup'),undefined);assert.equal(t.el('Open setup wizard'),undefined);
  await t.key('Escape');assert.equal(setupStep(t),'game');assert.equal(t.routeLog.at(-1),'/deck-fusion');
  await go(t,'target');await go(t,'features');
  await t.click('ReShade');assert.equal(draft(t).reshade.mode,'standalone');
  await t.click('OptiScaler');assert.equal(draft(t).reshade.mode,'opti');
  await t.click('OptiScaler');assert.equal(draft(t).reshade.mode,'standalone');
  await t.click('OptiScaler');await go(t,'injection');await go(t,'effects');
  assert.deepEqual(downloaded,['standard','extra'],'Every built-in pack is included, not only default packs');
  assert.ok(t.el('extra (extra.fx)'));await t.click('extra (extra.fx)');
  assert.deepEqual(draft(t).reshade.techniques,['extra@extra.fx']);assert.ok(draft(t).reshade.packs.includes('extra'));
  await t.click('Done');await go(t,'runtimes');await go(t,'frame');
  assert.equal(t.el('Respect Deck FPS limiter').getAttribute('aria-checked'),'true');
  await t.click('Respect Deck FPS limiter');await t.click('Back');assert.equal(setupStep(t),'runtimes');await go(t,'frame');
  assert.equal(t.el('Respect Deck FPS limiter').getAttribute('aria-checked'),'false');
  await go(t,'upscale');await t.click('Upscaling output: Keep existing output');await t.click('FSR 4 INT8');
  const fix='Install RDNA2 ghosting fix (FSR 4.1.1b)';assert.equal(t.el(fix).getAttribute('aria-checked'),'true');await t.click(fix);
  await go(t,'review');assert.ok(t.w.document.querySelector('dl.df-setup-summary'));
  assert.equal(t.w.document.querySelector('[role=switch]'),null,'Review is text, not duplicate feature switches');
  assert.equal(t.el('Components'),undefined);assert.equal(t.el('Library'),undefined);
  assert.match(t.w.document.querySelector('.df-setup-summary').textContent,/Through OptiScaler.*1 effects/);
  assert.equal(draft(t).opti.fsr4_rdna2_fix,false);
  assert.ok(!jobs(t).some(x=>['prepare','runtime_install','runtime_helper_install'].includes(x)),'No game/prefix changes before Apply');
  await t.click('Exit to Steam Home');t.fields.Navigation.Navigate('/deck-fusion');await settle(280);assert.equal(setupStep(t),'game');
  assert.equal(draft(t).lsfg.respect_deck_limiter,false,'Reopening respects the saved opt-out');
 }finally{await t.close();}
});
test('effects popup keeps all toggles, filters them, and scrolls with right stick without duplicate native clicks',{skip},async()=>{
 const t=await host({guided:true,native:true,prepare:({fixtures,profile})=>{
  profile.reshade.mode='standalone';
  fixtures.schema.shaders=Array.from({length:80},(_,i)=>({file:`Effect${i}.fx`,relative:`Effect${i}.fx`,uniforms:[],pack:'standard',techniques:[`Effect ${String(i).padStart(2,'0')}`]}));
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await go(t,'effects');
  const popup=t.w.document.querySelector('[aria-label="ReShade effects"][role=dialog]'),list=popup.querySelector('[data-df-scroll]');
  assert.equal(popup.querySelectorAll('[role=switch]').length,80);assert.ok(popup.contains(t.w.document.activeElement));
  assert.equal(t.el('Next').getAttribute('aria-disabled'),'true','Background setup controls cannot activate through an open popup');
  await t.click('Effect 79 (Effect79.fx)');assert.equal(draft(t).reshade.techniques.length,1);
  const input=popup.querySelector('input');input.focus();
  t.rawState.callback([{unControllerIndex:0,ulButtons:0,sRightStickX:0,sRightStickY:-24000}]);await settle(100);
  assert.ok(list.scrollTop>0,'Native mode uses right-stick packets to scroll the effects pane');
  const before=list.scrollTop;t.rawState.callback([{unControllerIndex:0,ulButtons:0,sRightStickX:0,sRightStickY:0}]);await settle(45);assert.equal(list.scrollTop,before);
  const set=Object.getOwnPropertyDescriptor(t.w.HTMLInputElement.prototype,'value').set;set.call(input,'79');input.dispatchEvent(new t.w.Event('input',{bubbles:true}));input.dispatchEvent(new t.w.Event('change',{bubbles:true}));await settle();
  assert.equal(popup.querySelectorAll('[role=switch]').length,1);assert.equal(popup.querySelector('[role=switch]').getAttribute('aria-checked'),'true');
  await t.click('Done');assert.equal(t.w.document.querySelector('[data-df-overlay]'),null);assert.equal(t.w.document.activeElement,t.el('Next'));
  assert.equal(draft(t).reshade.techniques[0],'Effect 79@Effect79.fx');assert.deepEqual(t.rawState.nativeCalls,[true]);
 }finally{await t.close();assert.equal(t.rawState.nativeCalls.at(-1),false);}
});
test('running game wins over remembered selection with backend fallback',{skip},async()=>{
 for(const viaRouter of [true,false]){
  const t=await host({guided:true,prepare:({fixtures,profile,fields})=>{
   const witcher={...profile,appid:'292030',name:'The Witcher 3',root:'/games/Witcher',exe:'/games/Witcher/witcher3.exe'};
   fixtures.state.games.push({appid:witcher.appid,name:witcher.name,root:witcher.root});
   fixtures.profile=({appid})=>appid===witcher.appid?witcher:profile;
   if(viaRouter)fields.Router={MainRunningApp:{appid:292030},RunningApps:[]};else fixtures.running_games=['292030'];
  }});
  try{assert.match(t.w.document.querySelector('.df-game').textContent,/The Witcher 3/);assert.equal(t.w.sessionStorage.getItem('deck-fusion-game'),'292030');assert.match(t.w.document.querySelector('.df-setup-notes').textContent,/Running game selected/);}
  finally{await t.close();}
 }
});
test('guided Apply automates helper and runtimes once, then commits graphics with a verified fresh plan',{skip},async()=>{
 const t=await host({guided:true,prepare:args=>{args.profile.setup.runtimes=['d3dcompiler_47','vcrun2022'];runtimeFixtures(args);}});
 try{
  await reachReview(t);assert.ok(!jobs(t).includes('runtime_install'));assert.ok(!jobs(t).includes('prepare'));
  await t.click('Apply this game');await settle(80);
  assert.equal(t.w.document.querySelector('.df-setup-heading h1').textContent,'Setup complete',t.w.document.body.textContent);
  const writes=t.calls.filter(x=>x.method==='start_job'&&['runtime_helper_install','runtime_install','prepare'].includes(x.args[0]));
  assert.deepEqual(writes.map(x=>x.args[0]),['runtime_helper_install','runtime_install','prepare']);
  assert.deepEqual(writes.map(x=>x.args[1].approval),['helper-token','runtime-token','after-runtime']);
  assert.deepEqual(Array.from(writes[1].args[1].runtimes),['d3dcompiler_47','vcrun2022']);assert.equal(writes[1].args[1].prefix,'/compat/123/pfx');
  await t.click('Return to Steam Home');assert.equal(t.routeLog.at(-1),'/library/home');
 }finally{await t.close();}
});
test('recorded runtimes are skipped and disabled feature stages disappear',{skip},async()=>{
 const t=await host({guided:true,prepare:args=>{
  runtimeFixtures(args);args.profile.lsfg.enabled=false;args.profile.setup.runtimes=['vcrun2022'];
  args.jobResults.runtime_status={prefix:'/compat/123/pfx',prefixes:['/compat/123/pfx'],helper:{available:false},blockers:[],runtimes:[{name:'vcrun2022',recorded:true}]};
 }});
 try{
  const visited=[setupStep(t)];while(setupStep(t)!=='review'){await t.click('Next');await settle(30);visited.push(setupStep(t));assert.ok(visited.length<10);}
  assert.deepEqual(visited,['game','target','features','runtimes','frame','review']);
  await t.click('Apply this game');await settle(80);assert.ok(!jobs(t).includes('runtime_install'));assert.ok(!jobs(t).includes('runtime_helper_install'));assert.ok(jobs(t).includes('prepare'));
 }finally{await t.close();}
});
test('changed plan and failed runtime prevent graphics writes while preserving guided navigation',{skip},async()=>{
 for(const failure of ['changed','runtime']){
  const t=await host({guided:true,prepare:args=>{args.profile.setup.runtimes=['vcrun2022'];runtimeFixtures(args);}});
  try{
   await reachReview(t);
   if(failure==='changed')t.jobResults.plan=payload=>({profile:payload.profile,approval_token:'changed',blockers:[{title:'Game started',detail:'Close the running game.'}],warnings:[],resolutions:[]});
   else t.jobResults.runtime_install=()=>{throw new Error('Installer cancelled. Prefix snapshot retained.');};
   await t.click('Apply this game');await settle(70);
   assert.equal(setupStep(t),'review');assert.ok(!jobs(t).includes('prepare'));assert.equal(t.w.document.querySelector('.df-nav'),null);
   if(failure==='changed'){assert.ok(!jobs(t).includes('runtime_install'));assert.equal(t.el('Apply this game').getAttribute('aria-disabled'),'true');}
   else assert.match(t.w.document.querySelector('[role=alert]').textContent,/Installer cancelled/);
   if(failure==='changed')await t.click('Close');
   await t.click('Back');assert.equal(setupStep(t),'frame');
  }finally{await t.close();}
 }
});
test('missing Lossless Scaling DLL can be resolved without leaving setup',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,jobResults})=>{
  fixtures.requirements=({profile})=>({items:[],needs_registration:profile.lsfg.enabled});
  jobResults.lsfg_setup=()=>{throw new Error('Purchased Lossless Scaling DLL not found.');};
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'runtimes');await go(t,'frame');await go(t,'lsfg');
  assert.equal(t.w.document.querySelector('.df-nav'),null);await t.click('Use LSFG');await go(t,'review');
  assert.notEqual(t.el('Apply this game').getAttribute('aria-disabled'),'true');
 }finally{await t.close();}
});

test('runtime completion never authorizes a changed graphics file plan',{skip},async()=>{
 const t=await host({guided:true,prepare:args=>{args.profile.setup.runtimes=['vcrun2022'];runtimeFixtures(args);}});
 try{
  await reachReview(t);
  const install=t.jobResults.runtime_install,plan=t.jobResults.plan;
  t.jobResults.runtime_install=payload=>{const result=install(payload);t.jobResults.plan=payload=>({...plan(payload),file_state:{'dxgi.dll':'changed-after-review'}});return result;};
  await t.click('Apply this game');await settle(70);
  assert.equal(setupStep(t),'review');assert.ok(jobs(t).includes('runtime_install'));assert.ok(!jobs(t).includes('prepare'));
  assert.match(t.w.document.querySelector('.df-status').textContent,/graphics plan changed/);
 }finally{await t.close();}
});

test('moved or ambiguous Proton prefixes stay recoverable inside guided setup',{skip},async()=>{
 const t=await host({guided:true,prepare:({profile,jobResults})=>{
  profile.setup.runtime_prefix='/old/123/pfx';profile.setup.runtimes=['vcrun2022'];
  jobResults.runtime_status=payload=>({prefix:payload.prefix||null,prefixes:['/ssd/123/pfx','/sdcard/123/pfx'],blockers:payload.prefix?[]:['Choose the Proton prefix.'],helper:{available:true},runtimes:[]});
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'runtimes');assert.equal(draft(t).setup.runtime_prefix,'');
  await t.click('Proton prefix: Select');await t.click('/sdcard/123/pfx');await settle(40);
  assert.equal(draft(t).setup.runtime_prefix,'/sdcard/123/pfx');
  await go(t,'frame');assert.equal(t.w.document.querySelector('.df-nav'),null);
 }finally{await t.close();}
});

test('auto API displays engine detection and checks the live renderer before downloads',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,profile})=>{
  profile.api='auto';fixtures.scan.candidates[0].api='auto';
  fixtures.detect_api={api:'dx11',source:'imports',note:'Renderer imports found in UnityPlayer.dll.'};
 }});
 try{
  await go(t,'target');assert.ok(t.el('Graphics API: Auto-detect · DirectX 11'));
  await go(t,'features');
  assert.ok(t.calls.some(x=>x.method==='rpc'&&x.args[0]==='detect_api'&&x.args[1].launch==='--skip-launcher'));
  assert.ok(!jobs(t).some(x=>['install','shader','prepare','runtime_install'].includes(x)));
 }finally{await t.close();}
});

test('unknown API remains on target until explicitly selected',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,profile})=>{
  profile.api='auto';fixtures.scan.candidates[0].api='auto';
  fixtures.detect_api={api:'auto',source:'ambiguous',note:'Several renderers are present. Select the API the game uses.'};
 }});
 try{
  await go(t,'target');await t.click('Next');await settle(30);
  assert.equal(setupStep(t),'target');assert.match(t.w.document.querySelector('[role=alert]').textContent,/Several renderers/);
  assert.ok(!jobs(t).some(x=>['install','shader','prepare','runtime_install'].includes(x)));
  await t.click('Graphics API: Auto-detect');await t.click('DirectX 11');await go(t,'features');
  assert.equal(draft(t).api,'dx11');
 }finally{await t.close();}
});

test('unavailable optional shader pack is reported without blocking available effects',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,jobResults,profile})=>{
  profile.reshade.mode='standalone';fixtures.schema.packs=[{id:'standard',name:'Standard'},{id:'legacy',name:'Legacy'}];
  fixtures.state.packages.shaders={standard:{path:'/cache/standard'}};
  fixtures.schema.shaders=[{file:'Test.fx',relative:'Test.fx',pack:'standard',techniques:['Test'],uniforms:[]}];
  jobResults.shader=()=>{throw new Error('SIMULATED unavailable optional pack');};
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await go(t,'effects');
  assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/Some packs could not be loaded/);
  await t.click('Test (Test.fx)');assert.deepEqual(Array.from(draft(t).reshade.techniques),['Test@Test.fx']);
  await t.click('Done');await t.click('Step information');
  assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/SIMULATED unavailable optional pack/);
 }finally{await t.close();}
});

test('required shader failure stays on injection and does not silently drop its selection',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,jobResults,profile})=>{
  profile.reshade.mode='standalone';profile.reshade.packs=['legacy'];profile.reshade.techniques=['Legacy@Legacy.fx'];
  fixtures.schema.packs=[{id:'legacy',name:'Legacy'}];
  fixtures.requirements={items:[{kind:'shader',id:'legacy',ready:false}]};
  jobResults.shader=()=>{throw new Error('SIMULATED selected pack unavailable');};
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await t.click('Next');await settle(30);
  assert.equal(setupStep(t),'injection');assert.match(t.w.document.querySelector('[role=alert]').textContent,/selected pack unavailable/);
  assert.deepEqual(Array.from(draft(t).reshade.techniques),['Legacy@Legacy.fx']);assert.ok(!jobs(t).includes('prepare'));
 }finally{await t.close();}
});

test('failed runtime refreshes its receipt and exposes installer output inside setup',{skip},async()=>{
 const t=await host({guided:true,prepare:args=>{
  args.profile.setup.runtimes=['vcrun2022'];runtimeFixtures(args);
  let failed=false;const status=args.jobResults.runtime_status;
  args.jobResults.runtime_status=()=>({...status(),last:failed?{error:'Prefix tool exited with status 1.',log_tail:'SIMULATED actual Windows installer failure'}:null});
  args.jobResults.runtime_install=()=>{failed=true;throw new Error('Prefix tool exited with status 1.');};
 }});
 try{
  await reachReview(t);await t.click('Apply this game');await settle(80);
  assert.equal(setupStep(t),'review');assert.ok(!jobs(t).includes('prepare'));
  await t.click('Installer log');
  assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/SIMULATED actual Windows installer failure/);
  assert.equal(t.w.document.querySelector('.df-nav'),null);
 }finally{await t.close();}
});

test('helper installation failure exposes its log without starting prefix or graphics work',{skip},async()=>{
 const t=await host({guided:true,prepare:args=>{
  args.profile.setup.runtimes=['vcrun2022'];runtimeFixtures(args);
  let failed=false;const status=args.jobResults.runtime_status;
  args.jobResults.runtime_status=()=>({...status(),helper_log:failed?{path:'/helper.log',text:'SIMULATED helper download failed'}:null});
  args.jobResults.runtime_helper_install=()=>{failed=true;throw new Error('Helper setup failed.');};
 }});
 try{
  await reachReview(t);await t.click('Apply this game');await settle(80);
  assert.ok(!jobs(t).includes('runtime_install'));assert.ok(!jobs(t).includes('prepare'));
  await t.click('Installer log');assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/SIMULATED helper download failed/);
 }finally{await t.close();}
});

test('a shader recovered by the required-dependency retry does not keep an unavailable warning',{skip},async()=>{
 const t=await host({guided:true,prepare:({fixtures,jobResults,profile})=>{
  profile.reshade.mode='standalone';profile.reshade.packs=['legacy'];
  fixtures.schema.packs=[{id:'legacy',name:'Legacy'}];
  fixtures.requirements=()=>({items:[{kind:'shader',id:'legacy',ready:!!fixtures.state.packages.shaders?.legacy}]});
  let attempts=0;
  jobResults.shader=()=>{
   if(++attempts===1)throw new Error('SIMULATED temporary failure');
   fixtures.state.packages.shaders={legacy:{path:'/cache/legacy'}};
   fixtures.schema.shaders=[{file:'Legacy.fx',relative:'Legacy.fx',pack:'legacy',techniques:['Legacy'],uniforms:[]}];return {};
  };
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await go(t,'effects');
  assert.ok(t.el('Legacy (Legacy.fx)'));
  assert.doesNotMatch(t.w.document.querySelector('[data-df-overlay]').textContent,/Some packs could not be loaded/);
 }finally{await t.close();}
});

test('native Steam scrolling is used without the removed raw-state API and keeps effect focus',{skip},async()=>{
 const t=await host({guided:true,native:true,raw:false,nativeScroll:true,prepare:({fixtures,profile})=>{
  profile.reshade.mode='standalone';fixtures.schema.shaders=Array.from({length:60},(_,i)=>({file:`S${i}.fx`,relative:`S${i}.fx`,pack:'standard',techniques:[`Shader ${i}`],uniforms:[]}));
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await go(t,'effects');
  const list=t.scrollBridge.element;assert.ok(list);assert.equal(t.scrollBridge.direction,'y');
  assert.equal(list.dataset.dfNativeScroll,'true');assert.ok(list.contains(t.w.document.activeElement));
  assert.equal(t.rawState.callback,null);assert.deepEqual(t.rawState.nativeCalls,[true]);
  // Native browser scroll events can target the page behind the popup if the
  // trackpad pointer was left there. Route them once to the active effects pane.
  list.scrollTop=0;
  const wheel=(target,deltaY,deltaMode=0)=>{const event=new t.w.WheelEvent('wheel',{deltaY,deltaMode,bubbles:true,cancelable:true});target.dispatchEvent(event);return event;};
  assert.equal(wheel(t.w.document.body,80).defaultPrevented,true);assert.equal(list.scrollTop,80);
  assert.equal(wheel(list,2,1).defaultPrevented,true);assert.equal(list.scrollTop,144);
  // The plugin's Gamepad fallback must not double native wheel scrolling.
  t.w.navigator.getGamepads=()=>[{connected:true,mapping:'standard',axes:[0,0,0,1]}];
  list.scrollTop=120;await settle(120);assert.equal(list.scrollTop,120);
  await t.click('Shader 2 (S2.fx)');assert.equal(draft(t).reshade.techniques.length,1);
  await t.click('Done');assert.equal(t.scrollBridge.element,null);
  assert.equal(wheel(t.w.document.body,80).defaultPrevented,false,'Popup scrolling is released on close');
 }finally{await t.close();assert.equal(t.rawState.nativeCalls.at(-1),false);}
});

test('legacy right-stick scroll holds until neutral and stops on focus loss',{skip},async()=>{
 const t=await host({guided:true,native:true,prepare:({fixtures,profile})=>{
  profile.reshade.mode='standalone';fixtures.schema.shaders=[{file:'A.fx',relative:'A.fx',pack:'standard',techniques:['A'],uniforms:[]}];
 }});
 try{
  await go(t,'target');await go(t,'features');await go(t,'injection');await go(t,'effects');
  const list=t.w.document.querySelector('[data-df-scroll]');
  t.rawState.callback([{unControllerIndex:0,ulButtons:0,sRightStickY:-24000}]);await settle(320);
  const first=list.scrollTop;await settle(320);assert.ok(list.scrollTop>first+50);
  t.w.dispatchEvent(new t.w.Event('blur'));const stopped=list.scrollTop;await settle(60);assert.equal(list.scrollTop,stopped);
  t.w.dispatchEvent(new t.w.Event('focus'));await settle(60);assert.equal(list.scrollTop,stopped);
 }finally{await t.close();}
});

function forceFixtures({jobResults,fixtures,profile}){
 jobResults.plan=payload=>payload.force_repair?{profile:payload.profile,force_repair:true,approval_token:'force-token',blockers:[],warnings:[],resolutions:[],changes:[],file_count:7,repairs:[{path:'bin/dxgi.dll',state:'missing'}],launch_after:'%command% --skip-launcher'}:
  {profile:payload.profile,force_repair:false,repair_available:true,blockers:[{title:'Tracked files missing',detail:'Managed files were deleted: bin/dxgi.dll'}],repairs:[{path:'bin/dxgi.dll',state:'missing'}]};
 jobResults.prepare=payload=>{Object.assign(profile,payload.profile);return {token:'prepared-token',launch_after:'%command% --skip-launcher'};};fixtures.finish={committed:true};
}

test('missing managed files open a force popup; cancellation is inert and force applies the exact plan',{skip},async()=>{
 const t=await host({guided:true,prepare:forceFixtures});
 try{
  await reachReview(t,true);let popup=t.w.document.querySelector('[data-df-overlay]');
  assert.match(popup.textContent,/Managed files were deleted/);assert.ok(t.el('Force apply settings'));
  assert.equal(t.el('Apply this game').getAttribute('aria-disabled'),'true');assert.ok(!jobs(t).includes('prepare'));
  await t.click('Cancel');assert.ok(!jobs(t).includes('prepare'));assert.equal(t.w.document.querySelector('[data-df-overlay]'),null);
  await t.click('Review force apply');await settle(40);await t.click('Force apply settings');await settle(80);
  const prepared=t.calls.find(x=>x.method==='start_job'&&x.args[0]==='prepare');
  assert.ok(prepared);assert.equal(prepared.args[1].force_repair,true);assert.equal(prepared.args[1].approval,'force-token');
  assert.equal(t.w.document.querySelector('[data-setup-done]').dataset.setupDone,'true');
 }finally{await t.close();}
});

test('force-popup acceptance cannot bypass a newly running game',{skip},async()=>{
 const t=await host({guided:true,prepare:forceFixtures});
 try{
  await reachReview(t,true);
  t.jobResults.plan=payload=>({profile:payload.profile,force_repair:payload.force_repair,blockers:[{title:'Game running',detail:'Close Baldur’s Gate 3 first.'}],warnings:[],resolutions:[]});
  await t.click('Force apply settings');await settle(60);
  assert.ok(!jobs(t).includes('prepare'));assert.ok(!jobs(t).includes('runtime_install'));
  assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/Close Baldur/);
  assert.equal(t.el('Force apply settings'),undefined);
 }finally{await t.close();}
});

test('launch cleanup has a separate warning, retains original for rollback and writes only after Apply',{skip},async()=>{
 const old='WINEDLLOVERRIDES="version,winmm=n,b" ~/LSFG %command% --skip-launcher';
 const t=await host({guided:true,initialLaunch:old,prepare:args=>{
  forceFixtures(args);
  args.fixtures.launch_cleanup=({launch})=>({before:launch,cleaned:'%command% --skip-launcher',after:'/app/launcher 123 -- %command% --skip-launcher',removed:['version,winmm=n,b','~/LSFG'],warnings:['These overrides can also load other mods.']});
 }});
 try{
  await reachReview(t,true);assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/Replace existing graphics launch options/);
  assert.ok(!jobs(t).includes('prepare'));await t.click('Cancel');assert.ok(!jobs(t).includes('prepare'));
  assert.ok(!t.calls.some(x=>x.method==='start_job'&&x.args[0]==='runtime_install'));
  await t.click('Refresh review');await settle(25);await t.click('Replace launch options');await settle(40);
  assert.match(t.w.document.querySelector('[data-df-overlay]').textContent,/Managed files were deleted/);
  await t.click('Force apply settings');await settle(80);
  const writes=t.calls.filter(x=>x.method==='start_job'&&x.args[0]==='prepare');assert.equal(writes.length,1);
  assert.equal(writes[0].args[1].launch_actual,old);assert.equal(writes[0].args[1].launch,'%command% --skip-launcher');
  assert.equal(writes[0].args[1].force_repair,true);
 }finally{await t.close();}
});
