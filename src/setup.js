/* Guided setup. Business operations remain in Manager and the existing backend. */
const SETUP_PHASES=['Game','Features','Runtimes','Performance','Review'];
function setupSteps(p){return [
 {id:'game',title:'Choose a game',phase:0},
 {id:'target',title:'Executable & graphics API',phase:0},
 {id:'features',title:'Choose features',phase:1},
 ...(p&&(p.opti.enabled||p.reshade.mode!=='off')?[{id:'injection',title:'DLL injection',phase:1}]:[]),
 ...(p&&p.reshade.mode!=='off'?[{id:'effects',title:'ReShade effects',phase:1}]:[]),
 {id:'runtimes',title:'Windows runtimes',phase:2},
 {id:'frame',title:'Frame pacing',phase:3},
 ...(p?.opti.enabled?[{id:'upscale',title:'Upscaling output',phase:3}]:[]),
 {id:'review',title:'Review & apply',phase:4}
];}
function normalizeReShade(p){if(p.reshade.mode!=='off')p.reshade.mode=p.opti.enabled?'opti':'standalone';return p;}
// Runtime installers may add prefix registry entries. Continue automatically only
// when the reviewed graphics files, settings, loader allocation and warnings match.
function sameGuidedGraphicsPlan(before,after){
 const stable=value=>{
  const result=copy(value);delete result.approval_token;delete result.dll_context;
  if(result.dll_summary)delete result.dll_summary.effective;
  return JSON.stringify(result);
 };
 return stable(before)===stable(after);
}
function setupEffects(schema,p){
 const items=new Map();
 for(const shader of schema.shaders||[])for(const name of shader.techniques||[]){
  const key=`${name}@${shader.file}`;
  if(!items.has(key))items.set(key,{key,name,pack:shader.pack,file:shader.file});
 }
 for(const key of p?.reshade.techniques||[])if(!items.has(key))items.set(key,{key,name:key.split('@')[0],pack:'',file:'Existing selection'});
 return [...items.values()].sort((a,b)=>a.name.localeCompare(b.name)||a.file.localeCompare(b.file));
}
function startupGame(games,remembered,runningIds=[],router){
 let live=[];try{live=[router?.MainRunningApp?.appid,...(router?.RunningApps||[]).map(g=>g.appid)].filter(Boolean).map(String);}catch{}
 const ids=[...live,...runningIds.map(String),remembered];
 return ids.map(id=>games.find(g=>String(g.appid)===id)).find(Boolean)||games[0];
}
const setupCSS=`
.df-setup .df-top{height:50px;padding:0 22px}.df-setup .df-brand{font-size:17px}.df-setup .df-beta{font-size:10px}.df-setup-main{flex:1;min-height:0;display:flex;flex-direction:column;padding:14px 24px 10px;gap:12px}.df-phase-list{display:flex;gap:6px;flex-shrink:0}.df-phase{flex:1;font-size:11px;color:#919bb0;border-top:2px solid #ffffff18;padding-top:6px}.df-phase[data-active=true]{color:var(--cyan);border-color:var(--cyan)}.df-setup-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-shrink:0}.df-setup-heading h1{font-size:25px;font-weight:600;letter-spacing:-.5px}.df-setup-body{flex:1;min-height:0;display:flex;flex-direction:column;gap:10px}.df-setup-fields{display:flex;flex-direction:column;gap:9px;min-height:0}.df-setup .df-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(160px,44%);gap:16px;padding:11px 14px;border-radius:9px;min-height:58px;flex-shrink:0}.df-setup .df-card-title strong{font-size:14px}.df-setup .df-card-action,.df-setup .df-switch{font-size:13px;min-height:32px}.df-setup .df-help{margin-left:8px}.df-setup .df-range-value{font-size:15px}.df-setup:not([data-setup-step=review]):not([data-setup-done=true]) .df-setup-notes{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.df-setup[data-setup-step=review] .df-setup-body{gap:6px}.df-setup-notes{font-size:12px;line-height:1.45;color:#aebbd0}.df-setup-notes p{margin:0 0 6px}.df-setup-controls{display:flex;gap:10px;align-items:center;flex-shrink:0;margin-top:auto}.df-setup-controls .df-primary{margin-left:auto;min-width:148px}.df-setup-controls>.df-subtle{margin-left:auto}.df-setup .df-footer{padding:7px 22px;min-height:30px}.df-setup-summary{margin:0;padding:0;display:flex;flex-direction:column;gap:0}.df-setup-summary>div{display:grid;grid-template-columns:140px minmax(0,1fr);padding:5px 0;border-bottom:1px solid #ffffff0c;gap:14px;font-size:13px;line-height:1.3}.df-setup-summary dt{color:#9eacc4}.df-setup-summary dd{margin:0;overflow-wrap:anywhere}.df-setup-summary dd[data-truncate=true]{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.df-setup-alert{font-size:12px;line-height:1.4;color:#f5ca91;display:flex;align-items:center;gap:10px}.df-setup-alert span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.df-setup-alert .df-btn{margin-left:auto;flex-shrink:0}.df-setup-bottom{display:flex;gap:8px;flex-wrap:wrap}.df-effects-list{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;touch-action:pan-y;padding:3px 6px 3px 3px;scrollbar-color:#64758d #111728;scrollbar-width:thin}.df-studio .df-effect{display:flex;width:100%!important;min-height:38px;padding:5px 10px;border-radius:5px;border:0;border-bottom:1px solid #ffffff0a;gap:14px;text-align:left;justify-content:space-between;font-size:13px}.df-effect-name{min-width:0;display:flex;align-items:baseline;gap:10px}.df-effect-name strong{font-size:13px;font-weight:500}.df-effect-name small{color:#9cabc1;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.df-effect-check{width:17px;height:17px;flex-shrink:0;border:1px solid #a3b2c4;border-radius:3px;display:grid;place-items:center}.df-effect[aria-checked=true] .df-effect-check{background:var(--cyan);color:#102723;border-color:var(--cyan)}
.df-setup[data-short=true] .df-top{height:42px}.df-setup[data-short=true] .df-setup-main{padding:8px 18px;gap:7px}.df-setup[data-short=true] .df-phase{font-size:10px;padding-top:4px}.df-setup[data-short=true] .df-setup-heading h1{font-size:20px}.df-setup[data-short=true] .df-card{padding:6px 12px;min-height:48px;gap:10px}.df-setup[data-short=true] .df-card-title strong{font-size:13px}.df-setup[data-short=true] .df-setup-fields{gap:6px}.df-setup[data-short=true] .df-setup-body{gap:6px}.df-setup[data-short=true]:not([data-setup-step=review]):not([data-setup-done=true]) .df-setup-notes{display:none}.df-setup[data-short=true] .df-card{min-height:42px;padding:4px 10px}.df-setup[data-short=true] .df-setup-heading .df-help{min-height:24px;padding:3px}.df-setup[data-short=true] .df-setup-controls .df-btn{padding:6px 10px}.df-setup[data-short=true] .df-setup-notes{font-size:11px}.df-setup[data-short=true] .df-setup-summary>div{font-size:12px;padding:2px 0;grid-template-columns:125px minmax(0,1fr)}.df-setup[data-short=true] .df-setup-controls .df-btn{min-height:30px}.df-setup[data-narrow=true] .df-card{grid-template-columns:1fr;gap:5px;padding:9px}.df-setup[data-narrow=true] .df-phase{font-size:9px}.df-setup[data-narrow=true] .df-setup-summary>div{grid-template-columns:96px minmax(0,1fr)}.df-setup[data-narrow=true] .df-setup-main{padding:10px 12px}.df-setup[data-narrow=true] .df-effect-name{display:block}
`;
/* Steam's browser action set sends wheel events for scrolling. Keep these in the
   open effects popup even when the pointer is over its header or the page behind
   it. The native panel owns focus; older clients retain the gamepad fallback. */
function useEffectListScroll(listRef,nativeScroll=false){
 useEffect(()=>{
  const el=listRef.current,doc=el?.ownerDocument,view=doc?.defaultView;if(!el||!view)return;
  const wheel=event=>{
   const scope=el.closest('[data-df-overlay]');
   if(!el.isConnected||doc.visibilityState==='hidden'||(doc.hasFocus&&!doc.hasFocus())||!scope||event.ctrlKey)return;
   const active=doc.activeElement;
   if(active!==doc.body&&!scope.contains(active))return;
   const pixels=event.deltaY*(event.deltaMode===1?32:event.deltaMode===2?el.clientHeight:1);
   if(!Number.isFinite(pixels)||!pixels)return;
   event.preventDefault();event.stopPropagation();el.scrollTop+=pixels;
  };
  doc.addEventListener('wheel',wheel,{capture:true,passive:false});
  const removeWheel=()=>doc.removeEventListener('wheel',wheel,true);
  if(nativeScroll)return removeWheel;
  let raf=null,disposed=false,last=0;
  const tick=now=>{if(disposed)return;const dt=Math.min(32,now-last||16);last=now;let y=0;
   if(now-Number(el.dataset.dfRawScroll||-Infinity)>=180){try{for(const pad of view.navigator.getGamepads?.()||[]){if(pad?.connected&&pad.mapping==='standard'&&Math.abs(pad.axes[3]||0)>.2){y=pad.axes[3];break;}}}catch{}}
   const scope=el.closest('[data-df-overlay]');
   if(doc.visibilityState!=='hidden'&&(!doc.hasFocus||doc.hasFocus())&&el.isConnected&&(scope?.contains(doc.activeElement)||doc.activeElement===doc.body)&&y){el.scrollTop+=y*dt*.65;}
   raf=view.requestAnimationFrame(tick);
  };raf=view.requestAnimationFrame(tick);
  return()=>{disposed=true;removeWheel();if(raf!==null)view.cancelAnimationFrame(raf);};
 },[]);
}
function EffectPicker({effects,selected,toggle,close,catalogIssue}){
 const [query,setQuery]=useState(''),root=useRef(null),list=useRef(null);
 useEffectListScroll(list,!!U.ScrollPanel);
 useEffect(()=>{(studioFocusable(list.current)[0]||studioFocusable(root.current)[0])?.focus({preventScroll:true});},[]);
 const matches=effects.filter(x=>`${x.name} ${x.file} ${x.pack}`.toLowerCase().includes(query.toLowerCase()));
 return h(U.Focusable,{ref:root,className:'df-overlay','data-df-overlay':true,role:'dialog','aria-modal':true,'aria-label':'ReShade effects',onCancel:e=>{e?.stopPropagation?.();close();}},
  h('div',{className:'df-overlay-head'},h('h2',null,'ReShade effects'),h(StudioButton,{'aria-label':'Close effects',onClick:close,className:'df-icon'},studioIcon('close'))),
  h('input',{'aria-label':'Search effects',placeholder:'Search effects…',value:query,onChange:e=>setQuery(e.target.value)}),
  h('div',{className:'df-subtle'},`${selected.length} enabled · ${matches.length} available · Right stick / touch to scroll`),
  catalogIssue&&h('div',{className:'df-subtle',role:'status'},'Some packs could not be loaded. Step information has the details.'),
  h(U.ScrollPanel||'div',{className:'df-effects-list','data-df-scroll':true,'data-df-native-scroll':!!U.ScrollPanel,...(U.ScrollPanel?{scrollDirection:'y'}:{}),ref:list,onFocusCapture:e=>scrollFocusedControl({target:e.target,currentTarget:list.current})},
   ...matches.map(effect=>h(StudioButton,{key:effect.key,className:'df-effect',role:'switch','aria-label':`${effect.name} (${effect.file})`,'aria-checked':selected.includes(effect.key),onClick:()=>toggle(effect,!selected.includes(effect.key))},h('span',{className:'df-effect-name'},h('strong',null,effect.name),h('small',null,effect.pack?`${effect.pack} / ${effect.file}`:effect.file)),h('span',{className:'df-effect-check','aria-hidden':true},selected.includes(effect.key)?'✓':''))),
   !matches.length&&h('p',{className:'df-subtle'},'No matching effects.')),
  h('div',{className:'df-overlay-foot'},h('span',{className:'df-subtle'},'Saved to this game’s draft.'),h(StudioButton,{className:'df-primary',onClick:close},'Done')));
}
function SetupPrompt({model,busy,confirm,cancel,pageRef}){
 const root=useRef(null),reader=useRef(null),[page,setPage]=useState(0);
 const chunks=useMeasuredPages(model.text,reader),current=Math.min(page,chunks.length-1);
 pageRef.current=direction=>setPage(x=>clampNumber(x+direction,0,chunks.length-1));
 useEffect(()=>{studioFocusable(root.current)[0]?.focus({preventScroll:true});},[]);
 return h(U.Focusable,{ref:root,className:'df-overlay','data-df-overlay':true,role:'dialog','aria-modal':true,'aria-label':model.title,onCancel:e=>{e?.stopPropagation?.();if(!busy)cancel();}},
  h('div',{className:'df-overlay-head'},h('h2',null,model.title)),
  h('div',{ref:reader,className:'df-reader','data-df-reader':true},chunks[current]),
  chunks.length>1&&h('div',{className:'df-overlay-foot'},h(StudioButton,{disabled:current===0||busy,onClick:()=>setPage(x=>x-1)},'Previous page'),h('span',{className:'df-subtle'},`${current+1} / ${chunks.length}`),h(StudioButton,{disabled:current===chunks.length-1||busy,onClick:()=>setPage(x=>x+1)},'Next page')),
  h('div',{className:'df-overlay-foot'},h(StudioButton,{disabled:busy,onClick:cancel},model.kind==='blocked'?'Close':'Cancel'),model.kind!=='blocked'&&h(StudioButton,{className:'df-primary',disabled:busy,onClick:confirm},model.label)));
}
function SetupStudio({frameRef,frameHeight,p,step,done,content,summary,review,busy,message,error,progress,onNext,onBack,onRefresh,onExit,effects,toggleEffect,runtimeJob,cancelRuntime,runtimeLog,effectIssues,prompt,onPromptConfirm,onPromptCancel,onForce}){
 const [size,setSize]=useState({width:1280,height:688}),[overlay,setOverlay]=useState(null),returnFocus=useRef(null),pageRef=useRef(null),cursor=useRef(null);
 const steps=setupSteps(p),index=steps.findIndex(x=>x.id===step),meta=steps[index]||{title:'Lossless Scaling DLL',phase:3};
 const inventory=studioInventory(content),short=size.height<550,narrow=size.width<650,locked=busy||!!overlay||!!prompt;
 const close=()=>{setOverlay(null);const view=frameRef.current?.ownerDocument.defaultView;view?.requestAnimationFrame(()=>{if(returnFocus.current?.isConnected)returnFocus.current.focus({preventScroll:true});(frameRef.current?.querySelector('.df-setup-controls .df-primary')||studioFocusable(frameRef.current)[0])?.focus({preventScroll:true});});};
 const open=model=>{returnFocus.current=frameRef.current?.ownerDocument.activeElement;setOverlay(model);};
 useEffect(()=>{if(prompt)return;const view=frameRef.current?.ownerDocument.defaultView;const timer=view?.requestAnimationFrame(()=>{const controls=frameRef.current?.querySelector('.df-setup-controls');if(controls&&!frameRef.current.contains(controls.ownerDocument.activeElement))studioFocusable(controls)[0]?.focus({preventScroll:true});});return()=>{if(timer!==undefined)view?.cancelAnimationFrame(timer);};},[prompt]);
 useStudioInput(frameRef,cursor,{back:()=>{if(prompt){if(!busy)onPromptCancel();}else if(overlay)close();else if(!busy)onBack();},page:direction=>{if(overlay||prompt)pageRef.current?.(direction);}});
 useEffect(()=>{const el=frameRef.current,view=el?.ownerDocument.defaultView;if(!el||!view)return;const measure=()=>setSize({width:el.clientWidth,height:el.clientHeight});measure();let observer;try{observer=new view.ResizeObserver(measure);observer.observe(el);}catch{}view.addEventListener('resize',measure);return()=>{observer?.disconnect();view.removeEventListener('resize',measure);};},[]);
 useEffect(()=>{setOverlay(step==='effects'?{type:'effects'}:null);if(step==='effects')return;const view=frameRef.current?.ownerDocument.defaultView;const timer=view?.requestAnimationFrame(()=>{const el=frameRef.current?.querySelector('.df-setup-fields');studioFocusable(el||frameRef.current)[0]?.focus({preventScroll:true});});return()=>{if(timer!==undefined)view?.cancelAnimationFrame(timer);};},[step]);
 const details=()=>open({type:'reader',title:'Apply details',text:[...((review?.blockers||[]).map(x=>`${x.title}\n${x.detail}`)),...(review?.resolutions||[]).map(x=>`${x.title}\n${x.before} → ${x.after}\n${x.detail}`),...(review?.conflicts||[]).map(x=>JSON.stringify(x)),...(review?.warnings||[]),...(p?.reshade.techniques||[])].join('\n\n')||'No additional details.'});
 return h(U.Focusable,{ref:frameRef,className:'df-studio df-setup','data-df-frame':true,'data-df-studio':true,'data-setup-step':step,'data-setup-done':done,'data-short':short,'data-narrow':narrow,style:{height:frameHeight},'flow-children':'column',onCancel:e=>{e?.stopPropagation?.();if(prompt){if(!busy)onPromptCancel();}else if(overlay)close();else if(!busy)onBack();}},h('style',null,studioCSS+setupCSS),h('div',{className:'df-atmosphere'}),
  h('header',{className:'df-top'},h('div',{className:'df-brand'},h('span',{className:'df-logo'},studioIcon('fusion',22)),'Deck Fusion'),h('span',{className:'df-beta'},'v0.3-beta6'),h('div',{className:'df-game'},h('strong',null,p?.name||'Choose a game')),h(StudioButton,{onClick:onExit,disabled:locked,'aria-label':'Exit to Steam Home',className:'df-icon'},studioIcon('close',18))),
  h('main',{className:'df-setup-main'},h('div',{className:'df-phase-list','aria-label':'Setup progress'},...SETUP_PHASES.map((title,i)=>h('span',{key:title,className:'df-phase','data-active':i===meta.phase||done,'aria-current':i===meta.phase?'step':undefined},`${i+1}  ${title}`))),
   h('div',{className:'df-setup-heading'},h('h1',null,done?'Setup complete':meta.title),!done&&inventory.notes.length>0&&h(StudioButton,{className:'df-help',disabled:locked,'aria-label':'Step information',onClick:()=>open({type:'reader',title:meta.title,text:inventory.notes.map(x=>x.text).join('\n\n')})},studioIcon('info',18)),!done&&h('span',{className:'df-subtle'},index<0?'LSFG setup':`${index+1} / ${steps.length}`)),
   h('div',{className:'df-setup-body'},
    done?h('div',{className:'df-setup-notes'},...inventory.notes.map((x,i)=>h('p',{key:i},x.text))):step==='review'?h(R.Fragment,null,
     h('dl',{className:'df-setup-summary'},...summary.map(([title,value])=>h('div',{key:title},h('dt',null,title),h('dd',{'data-truncate':title==='Executable',title:value},value)))),
          !review?.blockers?.length&&!error&&h('div',{className:'df-setup-notes'},'Apply backs up managed files and any selected runtime prefix before installation.'),
     review?.blockers?.length>0&&!error&&h('div',{className:'df-setup-alert'},h('span',null,review.blockers.map(x=>x.detail||x.title).join(' ')),h(StudioButton,{onClick:details,disabled:locked},'Details'))):h(R.Fragment,null,
      h('div',{className:'df-setup-fields'},...inventory.controls.map(item=>h(StudioField,{key:item.label,item,disabled:locked,open}))),
      step==='effects'&&h(StudioButton,{className:'df-primary',disabled:locked,onClick:()=>open({type:'effects'})},'Choose ReShade effects'),
      h('div',{className:'df-setup-notes'},...inventory.notes.map((x,i)=>h('p',{key:i},x.text)))),
    error&&h('div',{className:'df-setup-alert',role:'alert'},h('span',null,error),h(StudioButton,{disabled:locked,onClick:()=>open({type:'reader',title:'Operation details',text:error})},'Details'))),
   h('div',{className:'df-setup-controls'},!done&&h(StudioButton,{onClick:onBack,disabled:locked||step==='game'},'Back'),!done&&runtimeLog&&['runtimes','review'].includes(step)&&h(StudioButton,{disabled:locked,onClick:()=>open({type:'reader',title:'Runtime installer log',text:runtimeLog})},'Installer log'),!done&&step==='review'&&h(R.Fragment,null,h(StudioButton,{onClick:details,disabled:locked},'Details'),h(StudioButton,{onClick:onRefresh,disabled:locked,'aria-label':'Refresh review'},'Refresh'),h(StudioButton,{onClick:onForce,disabled:locked,'aria-label':'Review force apply'},'Force apply…')),h(StudioButton,{className:'df-primary',disabled:locked||(!done&&!p)||(!done&&step==='review'&&(!review?.approval_token||!!review.blockers?.length)),onClick:done?onExit:onNext},done?'Return to Steam Home':busy?'Working…':step==='review'?'Apply this game':'Next'))),
  h('footer',{className:'df-footer'},h('span',null,'D-pad / left stick · A select · B back'),h('span',{className:'df-status',role:'status'},message||'Draft'),runtimeJob&&h(StudioButton,{onClick:cancelRuntime},'Cancel installation')),
  progress!==null&&h('progress',{className:'df-progress',max:1,value:progress,'aria-label':'Operation progress'}),
  prompt?h(SetupPrompt,{key:prompt.kind+prompt.text,model:prompt,busy,confirm:onPromptConfirm,cancel:onPromptCancel,pageRef}):overlay&&(overlay.type==='effects'?h(EffectPicker,{effects,selected:p?.reshade.techniques||[],toggle:toggleEffect,close,catalogIssue:effectIssues}):h(StudioOverlay,{model:overlay,close,short,narrow,pageRef})));
}
