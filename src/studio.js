/* Deck Fusion Studio v0.3-beta5. Local UI only; all mutations use the existing Manager. */
const STUDIO_TABS=[
 ['library','Library','grid'], ['lsfg','Motion','wave'],
 ['opti','Upscaling','layers'], ['reshade','ReShade','spark'],
 ['wine','DLLs','link'], ['runtimes','Runtimes','cube'],
 ['apply','Apply','check'], ['tools','Tools','tool']
];
function exitStudio(){U.Navigation.Navigate('/library/home');U.Navigation.CloseSideMenus?.();}
function studioIcon(name,size=20){
 const paths={grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',wave:'M2 12h3l3-8 5 16 3-8h6',layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5',spark:'m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z',link:'M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2 M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2',cube:'m12 2 9 5v10l-9 5-9-5V7z M3 7l9 5 9-5 M12 12v10',check:'m5 12 4 4L19 6',tool:'m14 6 4 4 3-3a7 7 0 0 1-9 9l-7 6-3-3 6-7a7 7 0 0 1 9-9z',arrow:'m9 5 7 7-7 7',back:'m15 5-7 7 7 7',info:'M12 11v6 M12 7h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',close:'m6 6 12 12 M18 6 6 18',search:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',fusion:'M5 3h15v4H9v4h8v4H9v6H5z'};
 return h('svg',{width:size,height:size,viewBox:'0 0 24 24',fill:'none',stroke:'currentColor',strokeWidth:1.6,strokeLinecap:'round',strokeLinejoin:'round','aria-hidden':true},h('path',{d:paths[name]||paths.grid}));
}
const studioCSS=`
.df-studio{--cyan:#79f2df;--violet:#aca0ff;--ink:#0c101c;--muted:#a4adc3;position:relative;isolation:isolate;padding-top:var(--df-safe-top,48px);background:#0c101c;color:#edf1fa;font-family:Arial,Helvetica,sans-serif;font-size:14px;border-radius:12px;display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;min-width:0}
.df-studio *{box-sizing:border-box}.df-studio button,.df-studio input,.df-studio textarea{font:inherit}.df-studio button{cursor:pointer}.df-studio button:disabled,.df-studio [aria-disabled=true]{cursor:default;opacity:.4;pointer-events:none}.df-studio h1,.df-studio h2,.df-studio p{margin:0}.df-studio button,.df-studio input,.df-studio textarea{color:inherit}.df-studio button{width:auto;min-width:0}.df-studio :focus-visible,.df-studio .df-native-focus{outline:2px solid var(--cyan)!important;outline-offset:3px;box-shadow:0 0 0 5px #79f2df14!important}.df-studio :focus:not(:focus-visible){outline:none}.df-studio .df-native-focus{outline:2px solid var(--cyan)!important}
.df-atmosphere{position:absolute;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(ellipse at 78% 0%,#4838893d,transparent 53%),radial-gradient(ellipse at 26% 100%,#16444540,transparent 60%)}
.df-top{display:flex;align-items:center;gap:14px;height:70px;flex-shrink:0;padding:0 26px;border-bottom:1px solid #ffffff0e;background:#0a0e1780}.df-brand{display:flex;align-items:center;gap:11px;white-space:nowrap;font-size:18px;font-weight:700;letter-spacing:-.6px}.df-logo{display:grid;place-items:center;width:33px;height:37px;color:var(--cyan);background:linear-gradient(145deg,#25494280,#1c263a);border:1px solid #79f2df38;border-radius:10px}.df-beta{font:10px monospace;letter-spacing:1px;border:1px solid #aca0ff50;color:#c4bbff;padding:5px 7px;border-radius:5px;white-space:nowrap}.df-game{margin-left:auto;min-width:0;display:flex;flex-direction:column;gap:4px;text-align:right}.df-game strong{max-width:310px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.df-eyebrow{color:var(--muted);font-size:10px;letter-spacing:1.6px;text-transform:uppercase}.df-dirty{color:#f6c880;font-size:10px}.df-btn{display:flex;align-items:center;justify-content:center;gap:8px;min-height:36px;border:1px solid #ffffff1e;background:#ffffff06;border-radius:8px;padding:8px 12px;font-weight:600;font-size:12px;transition:background .15s,transform .15s}.df-btn:hover{background:#ffffff12}.df-btn.df-primary{background:var(--cyan);border-color:var(--cyan);color:#102723}.df-btn.df-primary:hover{background:#abffef}.df-btn.df-icon{padding:8px;flex-shrink:0}.df-btn.df-quiet{color:var(--muted)}
.df-body{display:flex;flex:1;min-height:0}.df-nav{width:176px;flex-shrink:0;display:flex;flex-direction:column;gap:5px;padding:24px 12px 16px;border-right:1px solid #ffffff0d;background:#0a0e1738}.df-nav-label{padding:0 12px 12px}.df-nav-button{justify-content:flex-start;gap:12px;border-color:transparent;min-height:40px;width:100%!important;padding:9px 13px;color:#a4adc3;font-weight:500}.df-nav-button[data-active=true]{background:linear-gradient(100deg,#79f2df17,#79f2df04);color:var(--cyan);border-color:#79f2df22;box-shadow:inset 2px 0 var(--cyan)}.df-nav-bottom{margin-top:auto;padding-top:12px}.df-nav-bottom .df-btn{width:100%;font-size:11px}.df-main{display:flex;flex-direction:column;flex:1;min-width:0;min-height:0;padding:20px 26px 14px;gap:12px}.df-hero{position:relative;flex-shrink:0;min-height:128px;display:flex;align-items:center;gap:18px;overflow:hidden}.df-hero-copy{flex:1;min-width:0;z-index:1}.df-hero h1{font-size:clamp(24px,3vw,36px);line-height:1.13;letter-spacing:-1.3px;font-weight:600;margin:9px 0}.df-hero p{font-size:13px;color:var(--muted);line-height:1.5}.df-hero .df-eyebrow{color:var(--cyan)}.df-orbit{width:192px;height:128px;position:relative;flex-shrink:0;display:grid;place-items:center;perspective:450px}.df-ring{position:absolute;width:142px;height:142px;border:1px solid #80f5db45;border-radius:50%;transform:rotateX(57deg) rotateZ(-25deg);box-shadow:0 0 30px #6febd414,inset 0 0 25px #80eed50c;animation:df-orbit 22s linear infinite}.df-ring:nth-child(2){width:115px;height:115px;border-color:#9d8df080;transform:rotateY(60deg) rotateZ(40deg);animation-name:df-orbit2;animation-duration:28s}.df-ring:nth-child(3){width:170px;height:170px;border-color:#afa0ff25;transform:rotateX(60deg) rotateY(35deg)}.df-orb{width:65px;height:65px;border-radius:18px;transform:rotate(-12deg);background:radial-gradient(circle at 30% 20%,#defff9,#6ce4d7 22%,#515694 65%,#202541);box-shadow:0 0 40px #79f2df20,inset -5px -8px 16px #10122b80;display:grid;place-items:center;color:#142b35}.df-orb svg{transform:rotate(12deg)}
.df-metric{z-index:2;position:absolute;bottom:4px;right:6px;border:1px solid #ffffff18;background:#111626e8;border-radius:8px;padding:7px 11px;font:11px monospace;color:var(--cyan)}.df-toolbar{display:flex;align-items:center;gap:8px;flex-shrink:0;min-height:34px}.df-toolbar-label{font-size:11px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-right:auto}.df-page-select{max-width:65%;min-width:0;overflow:hidden}.df-page-select span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.df-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(2,minmax(0,1fr));gap:12px;flex:1;min-height:0}.df-card{min-width:0;min-height:0;position:relative;padding:15px 17px;border:1px solid #ffffff12;border-radius:12px;background:linear-gradient(135deg,#2027388f,#161b2a9c);display:flex;flex-direction:column;justify-content:center;gap:9px;transition:border-color .18s,background .18s}.df-studio [data-pointer-hover=true]{outline:2px solid var(--cyan);outline-offset:2px}.df-card:hover{border-color:#ffffff2d;background:linear-gradient(135deg,#2932479e,#191f309e)}.df-card-title{display:flex;align-items:center;gap:6px;min-width:0}.df-card-title strong{font-size:13px;line-height:1.35;font-weight:500;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.df-help{margin-left:auto;flex-shrink:0;border:0!important;min-height:26px;padding:4px!important;color:#a4adc3;background:transparent!important}.df-card-action{justify-content:space-between;width:100%!important;text-align:left;min-height:38px;font-size:13px;font-weight:500}.df-card-action span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere;min-width:0}.df-card-action svg{flex-shrink:0}.df-switch{justify-content:space-between;background:transparent;border:0;padding:0;min-height:38px;width:100%!important;font-size:12px;color:#9aa7bc}.df-switch-track{position:relative;width:43px;height:24px;border:1px solid #ffffff22;background:#0b1020;border-radius:20px;transition:background .15s}.df-switch-track:after{content:'';position:absolute;top:4px;left:4px;width:14px;height:14px;background:#768096;border-radius:50%;transition:transform .15s}.df-switch[aria-checked=true] .df-switch-track{background:#79f2df;border-color:#79f2df}.df-switch[aria-checked=true] .df-switch-track:after{background:#163a36;transform:translateX(19px)}.df-switch[aria-checked=true]{color:var(--cyan)}
.df-range{display:flex;align-items:center;gap:8px}.df-range input{width:100%;min-width:0;height:30px;padding:0;background:transparent;accent-color:var(--cyan);cursor:pointer;border:0}.df-range-value{font:18px monospace;color:var(--cyan);margin-left:auto;white-space:nowrap}.df-range .df-btn{min-height:28px;padding:3px 8px;font-size:16px}.df-value{color:#b8c6da;font-size:13px;line-height:1.4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.df-pagination{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-shrink:0;height:39px}.df-page-count{font:11px monospace;color:var(--muted)}.df-dots{display:flex;gap:5px}.df-dot{height:3px;width:14px;background:#ffffff17;border-radius:3px}.df-dot[data-active=true]{width:25px;background:var(--cyan)}.df-notes{color:#ccc3fc;max-width:55%;font-size:11px}.df-notes[data-warning=true]{color:#f0c88b}.df-footer{flex-shrink:0;display:flex;align-items:center;gap:14px;border-top:1px solid #ffffff10;padding:10px 24px;color:#99a3b9;font-size:10px;min-height:36px}.df-key{display:inline-block;padding:2px 5px;border:1px solid #79829765;border-radius:4px;margin-right:5px;color:#d1d9e8;font:10px monospace}.df-status{margin-left:auto;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;min-width:0;max-width:40%}.df-status[data-error=true]{color:#f5bf84}.df-progress{position:absolute;bottom:0;left:0;width:100%;height:3px;accent-color:var(--cyan)}
.df-overlay{position:absolute;inset:var(--df-safe-top,48px) 0 0;z-index:20;padding:14px 18px;background:#0c101cf5;display:flex;flex-direction:column;gap:10px;overflow:hidden}.df-overlay-head{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-shrink:0}.df-overlay h2{font-size:22px;line-height:1.2;letter-spacing:-.5px;min-width:0;overflow-wrap:anywhere}.df-overlay-body{flex:1;min-height:0;display:flex;flex-direction:column;gap:10px}.df-overlay-foot{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-shrink:0}.df-overlay input,.df-overlay textarea{border:1px solid #ffffff28;background:#151c2d;border-radius:8px;padding:12px;min-width:0;width:100%;outline:0}.df-overlay textarea{resize:none;flex:1;min-height:50px;font-family:monospace;font-size:14px;line-height:1.5}.df-options{display:grid;grid-auto-rows:44px;align-content:start;gap:6px;flex:1;min-height:0;overflow:hidden}.df-studio .df-option{width:100%!important;height:44px;min-height:44px;max-height:44px;justify-content:space-between;text-align:left;padding:4px 12px;background:#1d2536;font-size:13px;gap:12px}.df-option svg{flex-shrink:0}.df-option span{min-width:0;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:17px}.df-option[data-selected=true]{border-color:#79f2df70;color:var(--cyan)}.df-reader{flex:1;min-height:0;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65;font-size:15px;color:#c6cee0;padding:18px 20px;background:#171e30;border:1px solid #ffffff12;border-radius:10px;overflow:hidden}.df-empty{grid-column:1/-1;grid-row:1/-1;display:flex;align-items:center;justify-content:center;text-align:center;color:var(--muted);line-height:1.7;padding:20px}.df-steps{display:flex;gap:6px;margin-top:12px}.df-step{flex:1;height:3px;border-radius:3px;background:#ffffff16}.df-step[data-active=true]{background:var(--cyan)}.df-wizard-actions{display:flex;gap:8px;flex-shrink:0}.df-wizard-actions .df-btn{flex:1}.df-cursor{position:absolute;z-index:40;pointer-events:none;left:0;top:0;color:#fff;filter:drop-shadow(0 2px 3px #000);will-change:transform;display:none}.df-subtle{color:var(--muted);font-size:12px}.df-reading-summary{font-size:12px;color:var(--muted);line-height:1.5}
@keyframes df-orbit{to{transform:rotateX(57deg) rotateZ(335deg)}}@keyframes df-orbit2{to{transform:rotateY(60deg) rotateZ(400deg)}}
.df-studio[data-short=true] .df-top{height:54px;padding:0 18px;gap:9px}.df-studio[data-short=true] .df-main{padding:10px 18px 8px;gap:7px}.df-studio[data-short=true] .df-hero{min-height:67px;max-height:78px}.df-studio[data-short=true] .df-hero h1{font-size:25px;margin:5px 0}.df-studio[data-short=true] .df-hero p{font-size:11px}.df-studio[data-short=true] .df-orbit{height:74px;width:120px;transform:scale(.68);transform-origin:right center}.df-studio[data-short=true] .df-grid{grid-template-rows:minmax(0,1fr);gap:8px}.df-studio[data-short=true] .df-nav{padding:9px 8px;gap:2px;width:143px}.df-studio[data-short=true] .df-nav-button{min-height:28px;padding:6px 9px;font-size:11px}.df-studio[data-short=true] .df-nav-label,.df-studio[data-short=true] .df-nav-bottom{display:none}.df-studio[data-short=true] .df-card{padding:10px 13px;gap:5px}.df-studio[data-short=true] .df-card-title strong{font-size:12px}.df-studio[data-short=true] .df-toolbar{min-height:30px}.df-studio[data-short=true] .df-pagination{height:32px}.df-studio[data-short=true] .df-footer{min-height:28px;padding:6px 18px;gap:8px;font-size:9px}.df-studio[data-short=true] .df-overlay{padding:16px;gap:10px}.df-studio[data-short=true] .df-reader{font-size:13px;padding:12px;line-height:1.5}.df-studio[data-short=true] .df-overlay h2{font-size:18px}.df-studio[data-short=true] .df-btn{min-height:30px;padding:6px 10px}.df-studio[data-short=true] .df-wizard-actions .df-btn{font-size:11px}.df-studio[data-short=true] .df-top .df-game strong{max-width:150px}.df-studio[data-short=true] .df-steps{margin-top:6px}
.df-studio[data-narrow=true] .df-nav{width:58px;padding:12px 6px}.df-studio[data-narrow=true] .df-nav-button{justify-content:center;padding:9px;min-height:37px}.df-studio[data-narrow=true] .df-nav-button span,.df-studio[data-narrow=true] .df-nav-label,.df-studio[data-narrow=true] .df-nav-bottom{display:none}.df-studio[data-narrow=true] .df-top{padding:0 12px}.df-studio[data-narrow=true] .df-brand{font-size:15px;gap:6px}.df-studio[data-narrow=true] .df-motion-control,.df-studio[data-narrow=true] .df-beta,.df-studio[data-narrow=true] .df-game{display:none}.df-studio[data-narrow=true] .df-top>.df-btn:first-of-type{margin-left:auto}.df-studio[data-narrow=true] .df-main{padding:12px;gap:9px}.df-studio[data-narrow=true] .df-orbit{display:none}.df-studio[data-narrow=true] .df-hero{min-height:95px}.df-studio[data-narrow=true] .df-hero h1{font-size:27px}.df-studio[data-narrow=true] .df-grid{grid-template-columns:minmax(0,1fr);grid-template-rows:repeat(2,minmax(0,1fr))}.df-studio[data-narrow=true] .df-toolbar-label{display:none}.df-studio[data-narrow=true] .df-page-select{max-width:100%;width:100%!important}.df-studio[data-narrow=true] .df-footer>span{display:none}.df-studio[data-narrow=true] .df-footer .df-status{display:block;max-width:100%;margin:0}.df-studio[data-narrow=true] .df-dots{display:none}.df-studio[data-narrow=true] .df-notes{max-width:45%}.df-studio[data-narrow=true] .df-card-title strong{font-size:13px}
.df-studio .df-hero{min-height:64px;max-height:76px}.df-studio .df-hero h1{font-size:26px;letter-spacing:-.6px;margin:0}.df-studio .df-orbit{height:64px;width:145px;transform:scale(.55);transform-origin:right center}.df-studio .df-metric{display:none}.df-studio .df-overlay h2{font-size:19px;line-height:24px;max-height:48px;overflow:hidden}.df-overlay input:not([type=range]){height:36px;flex-shrink:0;padding:7px 11px}.df-studio .df-overlay-head{min-height:32px}.df-studio .df-overlay-foot{min-height:32px}
@media(prefers-reduced-motion:reduce){.df-studio *{animation:none!important;transition:none!important}}.df-studio[data-motion=false] *{animation:none!important;transition:none!important}
`;
function studioText(node){
 if(node===null||node===undefined||typeof node==='boolean')return '';
 if(typeof node==='string'||typeof node==='number')return String(node);
 if(Array.isArray(node))return node.map(studioText).filter(Boolean).join('\n');
 const p=node.props||{};return [p.label,p.title,studioText(p.children)].filter(Boolean).join('\n');
}
function studioInventory(tree){
 const controls=[],notes=[];
 function visit(node,group=''){
  if(node===null||node===undefined||typeof node==='boolean')return;
  if(Array.isArray(node)){node.forEach(x=>visit(x,group));return;}
  if(typeof node!=='object'){if(String(node).trim())notes.push({title:group||'Good to know',text:String(node)});return;}
  const p=node.props||{},type=node.type;
  const kinds=[[U.ButtonItem,'button'],[U.DialogButton,'button'],[U.ToggleField,'toggle'],[U.TextField,'text'],[U.DropdownItem,'select'],[U.SliderField,'slider'],[RawEditorInput,'raw']];
  const match=kinds.find(([t])=>t&&t===type);
  if(match){controls.push({kind:match[1],label:String(p.label||studioText(p.children)||group||'Setting'),props:p,group});return;}
  if(type===U.PanelSection){visit(p.children,p.title||group);return;}
  if(type===U.PanelSectionRow||type===R.Fragment){visit(p.children,group);return;}
  function containsControl(x){if(!x||typeof x!=='object')return false;if(Array.isArray(x))return x.some(containsControl);return kinds.some(([t])=>t&&x.type===t)||x.type===U.PanelSection||containsControl(x.props?.children);}
  if(containsControl(p.children)){visit(p.children,group);return;}
  const content=studioText(node).trim();if(content)notes.push({title:group||'Good to know',text:content,warning:!!p['data-df-warning']});
 }
 visit(tree);return {controls,notes};
}
function clampNumber(value,min,max){return Math.min(max,Math.max(min,value));}
function StudioButton({children,onClick,disabled=false,className='',...props}){
 const fire=e=>{if(disabled)return;e?.stopPropagation?.();onClick?.(e);};
 return h(U.Focusable,{role:'button',tabIndex:disabled?-1:0,'aria-disabled':disabled||undefined,'data-df-focus':true,'data-df-disabled':disabled||undefined,focusClassName:'df-native-focus',className:`df-btn ${className}`,onActivate:fire,onClick:fire,
  onKeyDown:e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fire(e);}},...props},children);
}
function studioFocusable(root){if(!root)return [];return [...root.querySelectorAll('[data-df-focus],button,[role=button],input,textarea')].filter(x=>!x.disabled&&x.getAttribute('aria-disabled')!=='true'&&x.tabIndex!==-1&&x.getBoundingClientRect().width>0&&x.getBoundingClientRect().height>0);}
function studioMoveFocus(root,direction){
 const all=studioFocusable(root),doc=root.ownerDocument,active=doc.activeElement;
 if(!all.length)return;
 if(!all.includes(active)){all[0].focus({preventScroll:true});return;}
 const a=active.getBoundingClientRect(),ax=a.x+a.width/2,ay=a.y+a.height/2;
 const [dx,dy]=({left:[-1,0],right:[1,0],up:[0,-1],down:[0,1]})[direction];
 const scored=all.filter(x=>x!==active).map(el=>{const b=el.getBoundingClientRect(),bx=b.x+b.width/2-ax,by=b.y+b.height/2-ay;const forward=bx*dx+by*dy,cross=Math.abs(bx*dy-by*dx);return {el,forward,score:forward+cross*2.5};}).filter(x=>x.forward>4).sort((a,b)=>a.score-b.score);
 scored[0]?.el.focus({preventScroll:true});
}
/* Uses the rendered document's realm, not Decky's hidden module Window. Native
   Steam handles focus navigation. This hook adds physical mouse, keyboard and a
   route-scoped right-pad/right-stick pointer without editing any Steam layout. */
function useStudioInput(frameRef,cursorRef,actions){
 const live=useRef(actions);live.current=actions;
 useEffect(()=>{
  const frame=frameRef.current,doc=frame?.ownerDocument,view=doc?.defaultView;if(!view)return;
  let disposed=false,subscription=null,controllerList=null,raf=null,lastTime=0,lastPacket=0,buttons=0,previousPad=null,pointer={x:200,y:160},stick={x:0,y:0},hover=null,controller=null;
  const ownedModal=()=>doc.querySelector('[data-df-owned-dialog]')?.closest('.df-owned-modal,[role=dialog]');
  const scope=()=>ownedModal()||frame.querySelector('[data-df-overlay]')||frame;
  const scrollPane=()=>scope().querySelector('[data-df-scroll]');
  // A DOM-owned cursor lives above Decky's modal portal and is removed on teardown.
  const cursor=doc.createElement('div');cursor.setAttribute('aria-hidden','true');cursor.style.cssText='position:fixed;z-index:2147483000;pointer-events:none;display:none;left:0;top:0;filter:drop-shadow(0 2px 3px #000)';cursor.innerHTML='<svg width=22 height=26 viewBox="0 0 22 26"><path d="M2 1v21l6-6 5 9 4-2-5-9h8z" fill="white" stroke="#172233" stroke-width="1.4"/></svg>';doc.body.appendChild(cursor);
  const available=()=>!disposed&&frame.isConnected&&doc.visibilityState!=='hidden'&&(!doc.hasFocus||doc.hasFocus())&&frame.getBoundingClientRect().width>0;
  const paint=()=>{const r=frame.getBoundingClientRect(),scale=r.width/frame.offsetWidth||1;cursor.style.display='block';cursor.style.transform=`translate(${r.left+pointer.x*scale}px,${r.top+pointer.y*scale}px)`;};
  const atPointer=()=>{const r=frame.getBoundingClientRect(),scale=r.width/frame.offsetWidth||1;const target=doc.elementFromPoint(r.left+pointer.x*scale,r.top+pointer.y*scale);return target&&scope().contains(target)?target:null;};
  const move=(dx,dy)=>{pointer.x=clampNumber(pointer.x+dx,4,frame.clientWidth-18);pointer.y=clampNumber(pointer.y+dy,4,frame.clientHeight-18);paint();const next=atPointer()?.closest('[data-df-focus],button,[role=button],input,textarea');if(hover!==next){hover?.removeAttribute('data-pointer-hover');hover=next;hover?.setAttribute('data-pointer-hover','true');}};
  const click=()=>{const target=atPointer()?.closest('[data-df-focus],button,[role=button],input,textarea');if(!target||target.disabled||target.getAttribute('aria-disabled')==='true')return;target.focus({preventScroll:true});
   if(target.tagName==='INPUT'&&target.type==='range'){const r=target.getBoundingClientRect(),outer=frame.getBoundingClientRect(),scale=outer.width/frame.offsetWidth||1;const ratio=clampNumber((outer.left+pointer.x*scale-r.left)/r.width,0,1),min=Number(target.min),max=Number(target.max),step=Number(target.step)||1;const value=clampNumber(Math.round((min+ratio*(max-min))/step)*step,min,max);Object.getOwnPropertyDescriptor(view.HTMLInputElement.prototype,'value').set.call(target,String(value));target.dispatchEvent(new view.Event('input',{bubbles:true}));target.dispatchEvent(new view.Event('change',{bubbles:true}));}
   else target.click();
  };
  const key=e=>{
   if(e.defaultPrevented||!available()||!scope().contains(e.target))return;
   const editing=e.target.matches('input:not([type=range]),textarea');
   if(e.key==='Escape'){if(ownedModal())return;e.preventDefault();e.stopPropagation();live.current.back();return;}
   if(editing)return;
   const direction={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down'}[e.key];
   if(direction&&!(e.target.matches('input[type=range]')&&['left','right'].includes(direction))){e.preventDefault();e.stopPropagation();studioMoveFocus(scope(),direction);}
   if(e.key==='PageDown'||e.key==='PageUp'){e.preventDefault();live.current.page(e.key==='PageDown'?1:-1);}
   if(e.key==='Tab'){const all=studioFocusable(scope()),idx=all.indexOf(doc.activeElement),next=e.shiftKey?(idx<=0?all.length-1:idx-1):(idx+1)%all.length;e.preventDefault();all[next]?.focus({preventScroll:true});}
  };
  const physical=()=>{cursor.style.display='none';hover?.removeAttribute('data-pointer-hover');hover=null;};
  doc.addEventListener('keydown',key);doc.addEventListener('pointermove',physical);
  const candidates=[view.SteamClient?.Input,globalThis.SteamClient?.Input].filter(Boolean);
  const input=candidates.find(x=>typeof x.SetWebBrowserActionset==='function');
  const rawInput=candidates.find(x=>typeof x.RegisterForControllerStateChanges==='function');
  let nativeEnabled=false,nativeSupported=typeof input?.SetWebBrowserActionset==='function',windowActive=true;
  const setNative=enabled=>{if(!nativeSupported||enabled===nativeEnabled)return;try{input.SetWebBrowserActionset(enabled);nativeEnabled=enabled;}catch{nativeSupported=false;}};
  const syncNative=()=>{const focused=doc.activeElement;setNative(windowActive&&frame.isConnected&&doc.visibilityState!=='hidden'&&(!focused||focused===doc.body||frame.contains(focused)||!!ownedModal()?.contains(focused)));};
  const resetStick=()=>{stick={x:0,y:0};controller=null;previousPad=null;buttons=0;};
  const blur=()=>{windowActive=false;resetStick();setNative(false);physical();};
  const focus=()=>{windowActive=true;syncNative();};
  view.addEventListener('blur',blur);view.addEventListener('focus',focus);doc.addEventListener('visibilitychange',syncNative);doc.addEventListener('focusin',syncNative);
  syncNative();
  try{if(typeof rawInput?.RegisterForControllerStateChanges==='function')subscription=rawInput.RegisterForControllerStateChanges(changes=>{
   if(!available()){previousPad=null;stick={x:0,y:0};buttons=0;return;}
   if(scrollPane()?.dataset.dfNativeScroll==='true'){resetStick();return;}
   if(nativeSupported&&!scrollPane()){resetStick();return;}
   for(const state of changes||[]){
    const nextButtons=Number(state.ulButtons)||0,touch=!!(nextButtons&(1<<20)),sx=Number(state.sRightStickX)||0,sy=Number(state.sRightStickY)||0;
    if(controller!==null&&controller!==state.unControllerIndex)continue;
    if(controller===null&&(touch||Math.abs(sx)>6500||Math.abs(sy)>6500||(nextButtons&((1<<18)|(1<<26)))))controller=state.unControllerIndex;
    if(controller===null)continue;
    lastPacket=view.performance.now();stick={x:Math.abs(sx)>6500?sx/32767:0,y:Math.abs(sy)>6500?-sy/32767:0};
    if(nativeSupported)continue;
    if(touch&&Number.isFinite(state.sRightPadX)&&Number.isFinite(state.sRightPadY)){const pad={x:state.sRightPadX,y:state.sRightPadY};if(previousPad)move((pad.x-previousPad.x)*frame.clientWidth/54000,-(pad.y-previousPad.y)*frame.clientHeight/54000);previousPad=pad;}else previousPad=null;
    const clickMask=(1<<18)|(1<<26);if((nextButtons&clickMask)&&!(buttons&clickMask))click();buttons=nextButtons;
   }
  });}catch{/* Steam builds without raw reporting keep native focus and mouse. */}
  try{controllerList=rawInput?.RegisterForControllerListChanges?.(resetStick);}catch{}
  const tick=now=>{if(disposed)return;const dt=Math.min(32,now-lastTime||16);lastTime=now;const pane=scrollPane();if(!available()||pane?.dataset.dfNativeScroll==='true'||(!pane&&now-lastPacket>250))resetStick();if(available()&&(stick.x||stick.y)){if(pane&&(scope().contains(doc.activeElement)||doc.activeElement===doc.body)){pane.scrollTop+=stick.y*dt*.65;pane.dataset.dfRawScroll=String(now);}else if(!nativeSupported)move(stick.x*dt*.7,stick.y*dt*.7);}raf=view.requestAnimationFrame(tick);};
  if(subscription)raf=view.requestAnimationFrame(tick);
  return()=>{disposed=true;setNative(false);view.removeEventListener('blur',blur);view.removeEventListener('focus',focus);doc.removeEventListener('visibilitychange',syncNative);doc.removeEventListener('focusin',syncNative);try{subscription?.unregister?.();controllerList?.unregister?.();}catch{}if(raf!==null)view.cancelAnimationFrame(raf);doc.removeEventListener('keydown',key);doc.removeEventListener('pointermove',physical);hover?.removeAttribute('data-pointer-hover');cursor.remove();};
 },[]);
}
function StudioField({item,open,disabled}){
 const p=item.props,locked=disabled||p.disabled,label=item.label;
 const help=p.description?h(StudioButton,{className:'df-help',disabled:locked,onClick:()=>open({type:'reader',title:label,text:String(p.description)}),'aria-label':`Help: ${label}`},studioIcon('info',16)):null;
 let control;
 if(item.kind==='toggle')control=h(StudioButton,{className:'df-switch',role:'switch','aria-label':label,'aria-checked':!!p.checked,disabled:locked,onClick:()=>p.onChange(!p.checked)},p.checked?'Enabled':'Disabled',h('span',{className:'df-switch-track','aria-hidden':true}));
 else if(item.kind==='slider'){
  const update=direction=>p.onChange(Number(clampNumber(Number(p.value)+direction*Number(p.step),p.min,p.max).toFixed(5)));
  control=h('div',{className:'df-range'},h(StudioButton,{'aria-label':`Decrease ${label}`,disabled:locked||p.value<=p.min,onClick:()=>update(-1)},'−'),h(U.Focusable,{onActivate:e=>{if(locked)return;e?.stopPropagation?.();open({type:'range',item});},onKeyDown:e=>{if(locked)return;if(e.key==='Enter'){e.preventDefault();e.stopPropagation();open({type:'range',item});}else if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();e.stopPropagation();update(e.key==='ArrowLeft'?-1:1);}},onButtonDown:e=>{if(!locked&&(e.detail?.button===11||e.detail?.button===12)){e.stopPropagation();update(e.detail.button===11?-1:1);}},'aria-label':`Adjust ${label}`,'data-df-focus':true,tabIndex:locked?-1:0,'aria-disabled':locked||undefined,focusClassName:'df-native-focus',style:{flex:1,minWidth:0}},h('input',{type:'range','aria-label':label,min:p.min,max:p.max,step:p.step,value:p.value,disabled:locked,tabIndex:-1,onChange:e=>p.onChange(Number(e.target.value))})),h(StudioButton,{'aria-label':`Increase ${label}`,disabled:locked||p.value>=p.max,onClick:()=>update(1)},'+'));
 }else if(item.kind==='select'){
  const selected=p.rgOptions.find(x=>x.data===p.selectedOption);
  control=h(StudioButton,{className:'df-card-action',disabled:locked,onClick:()=>open({type:'select',title:label,options:p.rgOptions,value:p.selectedOption,choose:p.onChange}),'aria-label':`${label}: ${selected?.label||'Select'}`},h('span',null,selected?.label||'Select…'),studioIcon('arrow',17));
 }else if(item.kind==='text'||item.kind==='raw')control=h(StudioButton,{className:'df-card-action',disabled:locked,onClick:()=>open({type:'edit',title:label,value:String(p.value??''),raw:item.kind==='raw',save:value=>p.onChange(item.kind==='raw'?value:{target:{value}})}),'aria-label':`Edit ${label}`},h('span',null,p.value||'Tap to enter…'),studioIcon('tool',16));
 else if(item.kind==='info')control=h(StudioButton,{className:'df-card-action',onClick:()=>open({type:'reader',title:label,text:p.value}),'aria-label':`Read ${label}`},h('span',null,p.value.split('\n').slice(1).join(' ')||p.value),studioIcon('info',17));
 else control=h(StudioButton,{className:'df-card-action',disabled:locked,onClick:p.onClick,'aria-label':label},h('span',null,label),studioIcon('arrow',17));
 return h('div',{className:'df-card','data-df-card':label},h('div',{className:'df-card-title'},h('strong',null,item.kind==='button'?(item.group||'Action'):label),item.kind==='slider'&&h('span',{className:'df-range-value'},Number(p.value).toFixed(Number.isInteger(Number(p.value))?0:2)),help),control);
}
function useMeasuredPages(text,readerRef){
 const [chunks,setChunks]=useState([String(text||'')]);
 useEffect(()=>{
  const element=readerRef.current,view=element?.ownerDocument.defaultView;if(!element||!view)return;
  let disposed=false,observer,scheduled=null;
  const measure=()=>{
   scheduled=null;if(disposed||!element.clientWidth||!element.clientHeight)return;
   const probe=element.cloneNode(false);probe.removeAttribute('data-df-reader');probe.removeAttribute('id');
   probe.style.cssText+=`;position:fixed;visibility:hidden;pointer-events:none;left:-10000px;top:0;flex:none;width:${element.clientWidth}px;height:${element.clientHeight}px;`;
   element.parentElement.appendChild(probe);
   const result=[];let rest=String(text||'');
   while(rest.length){
    let low=1,high=rest.length,best=1;
    while(low<=high){const mid=Math.floor((low+high)/2);probe.textContent=rest.slice(0,mid);if(probe.scrollHeight<=probe.clientHeight+1){best=mid;low=mid+1;}else high=mid-1;}
    // Keep words whole where possible, while preserving every original character.
    if(best<rest.length){const boundary=Math.max(rest.lastIndexOf(' ',best-1),rest.lastIndexOf('\n',best-1));if(boundary>best*.6)best=boundary+1;}
    result.push(rest.slice(0,best));rest=rest.slice(best);
   }
   probe.remove();setChunks(result.length?result:['']);
  };
  const schedule=()=>{if(scheduled===null)scheduled=view.requestAnimationFrame(measure);};
  measure();try{observer=new view.ResizeObserver(schedule);observer.observe(element);}catch{}
  view.addEventListener('resize',schedule);
  return()=>{disposed=true;observer?.disconnect();view.removeEventListener('resize',schedule);if(scheduled!==null)view.cancelAnimationFrame(scheduled);};
 },[text]);
 return chunks;
}
/* Rendered inside Decky's modal focus trap. The original confirmation callbacks
   and approvals remain native; details are paginated instead of scrolling. */
function StudioReviewContent({children}){
 const inventory=studioInventory(children),reader=useRef(null),[page,setPage]=useState(0);
 const all=inventory.notes.map(x=>x.text).join('\n\n'),chunks=useMeasuredPages(all,reader),current=Math.min(page,chunks.length-1);
 return h(U.Focusable,{'data-df-owned-dialog':true,className:'df-studio',style:{height:'max(90px, min(370px, calc(100vh - 310px)))',width:'100%',minWidth:0,padding:12,gap:10},onKeyDown:e=>{if(e.key==='PageDown'||e.key==='PageUp'){e.preventDefault();e.stopPropagation();setPage(x=>clampNumber(x+(e.key==='PageUp'?-1:1),0,chunks.length-1));}},onButtonDown:e=>{if(e.detail?.button===7||e.detail?.button===8){e.stopPropagation();setPage(x=>clampNumber(x+(e.detail.button===7?-1:1),0,chunks.length-1));}}},h('style',null,studioCSS),
  h('div',{ref:reader,className:'df-reader','data-df-reader':true,style:{fontSize:13,lineHeight:1.5,padding:12}},chunks[current]),
  h('div',{className:'df-overlay-foot'},h(StudioButton,{disabled:current===0,onClick:()=>setPage(x=>Math.max(0,x-1))},'Previous'),h('span',{className:'df-page-count'},`${current+1} / ${chunks.length}`),...inventory.controls.filter(x=>x.kind==='button').map(x=>h(StudioButton,{key:x.label,onClick:()=>{x.props.onClick();setPage(0);}},x.label)),h(StudioButton,{disabled:current===chunks.length-1,onClick:()=>setPage(x=>x+1)},'Next')));
}
function StudioOverlay({model,close,short,narrow,pageRef}){
 const [query,setQuery]=useState(''),[page,setPage]=useState(0),[value,setValue]=useState(model.value||''),[range,setRange]=useState(model.item?.props.value),root=useRef(null),reader=useRef(null),optionsRef=useRef(null);
 const [perPage,setPerPage]=useState(1);
 useEffect(()=>{
  const el=optionsRef.current,view=el?.ownerDocument.defaultView;if(!el||!view)return;
  const measure=()=>{if(el.clientHeight>0)setPerPage(Math.max(1,Math.floor((el.clientHeight+6)/50)));};
  measure();let observer;try{observer=new view.ResizeObserver(measure);observer.observe(el);}catch{}
  view.addEventListener('resize',measure);return()=>{observer?.disconnect();view.removeEventListener('resize',measure);};
 },[model.type,short,narrow]);
 const list=(model.options||[]).filter(x=>String(x.label).toLowerCase().includes(query.toLowerCase()));
 const chunks=useMeasuredPages(model.type==='reader'?model.text:'',reader);
 const count=Math.max(1,model.type==='reader'?chunks.length:Math.ceil(list.length/perPage)),current=Math.min(page,count-1);
 pageRef.current=direction=>setPage(x=>clampNumber(x+direction,0,count-1));
 useEffect(()=>{const el=root.current;if(!el)return;const first=studioFocusable(el)[0];first?.focus({preventScroll:true});},[]);
 useEffect(()=>{const el=root.current;if(el&&!el.contains(el.ownerDocument.activeElement))studioFocusable(optionsRef.current||el)[0]?.focus({preventScroll:true});},[current,perPage,query]);
 const confirm=()=>{if(model.type==='edit')model.save(value);if(model.type==='range')model.item.props.onChange(Number(range));close();};
 return h(U.Focusable,{'data-df-overlay':true,ref:root,className:'df-overlay',role:'dialog','aria-modal':true,'aria-label':model.title||model.item?.label,onCancel:e=>{e?.stopPropagation?.();close();}},
  h('div',{className:'df-overlay-head'},h('div',null,h('h2',null,model.title||model.item?.label)),h(StudioButton,{onClick:close,'aria-label':'Close panel',className:'df-icon'},studioIcon('close'))),
  h('div',{className:'df-overlay-body'},
   model.type==='select'&&h(R.Fragment,null,h('input',{'aria-label':'Filter options',placeholder:'Search options…',value:query,onChange:e=>{setQuery(e.target.value);setPage(0);}}),h('div',{className:'df-options',ref:optionsRef},list.slice(current*perPage,(current+1)*perPage).map((x,i)=>h(StudioButton,{key:String(x.data)+i,className:'df-option','data-selected':x.data===model.value,onClick:()=>{model.choose(x);close();}},h('span',null,x.label),x.data===model.value?studioIcon('check',18):studioIcon('arrow',16))),!list.length&&h('div',{className:'df-empty'},'No matching options.'))),
   model.type==='reader'&&h('div',{ref:reader,className:'df-reader','data-df-reader':true},chunks[current]),
   model.type==='edit'&&h(R.Fragment,null,h('div',{className:'df-subtle'},'Changes stay in your draft until you apply. Use your keyboard, or Steam + X for the on-screen keyboard.'),model.raw?h('textarea',{'aria-label':model.title,value,spellCheck:false,onChange:e=>setValue(e.target.value)}):h('input',{'aria-label':model.title,value,onChange:e=>setValue(e.target.value),onKeyDown:e=>{if(e.key==='Enter')confirm();}})),
   model.type==='range'&&h(R.Fragment,null,h('div',{className:'df-reader'},h('div',{className:'df-range-value',style:{fontSize:48,marginBottom:16}},Number(range).toFixed(Number.isInteger(Number(range))?0:2)),h('input',{type:'range','aria-label':model.item.label,min:model.item.props.min,max:model.item.props.max,step:model.item.props.step,value:range,onChange:e=>setRange(Number(e.target.value))}),h('div',{className:'df-range',style:{marginTop:12}},h(StudioButton,{onClick:()=>setRange(x=>clampNumber(Number((x-model.item.props.step).toFixed(5)),model.item.props.min,model.item.props.max))},'− Decrease'),h(StudioButton,{onClick:()=>setRange(x=>clampNumber(Number((x+model.item.props.step).toFixed(5)),model.item.props.min,model.item.props.max))},'+ Increase'))))),
  h('div',{className:'df-overlay-foot'},(model.type==='edit'||model.type==='range')?h(R.Fragment,null,h(StudioButton,{onClick:close},'Cancel'),h(StudioButton,{className:'df-primary',onClick:confirm},'Save to draft')):h(R.Fragment,null,h(StudioButton,{disabled:current===0,onClick:()=>setPage(x=>Math.max(0,x-1))},'Previous'),h('span',{className:'df-page-count','aria-live':'polite'},`${current+1} / ${count}`),h(StudioButton,{disabled:current>=count-1,onClick:()=>setPage(x=>x+1)},'Next'))));
}
function Studio({frameRef,frameHeight,tabs,tab,setTab,p,dirty,busy,message,error,progress,onApply,runtimeJob,cancelRuntime}){
 const [size,setSize]=useState({width:1280,height:688}),[pages,setPages]=useState({}),[overlay,setOverlay]=useState(null),[motion,setMotion]=useState(()=>{try{return sessionStorage.getItem('deck-fusion-motion')!=='off';}catch{return true;}});
 const cursorRef=useRef(null),overlayPage=useRef(null),returnFocus=useRef(null),previousKey=useRef('');
 const key=`${tab}-${p?.appid||''}`;
 const short=size.height<550,narrow=size.width<650,pageSize=short||narrow?2:4;
 const inventory=studioInventory(tabs.find(x=>x[0]===tab)?.[2]);
 // Keep Library's common path together; the original advanced controls follow it.
 if(tab==='library'){const priority=['Find a game','Installed game','Actual executable','Rendering API'];inventory.controls.sort((a,b)=>{const ai=priority.indexOf(a.label),bi=priority.indexOf(b.label);return (ai<0?999:ai)-(bi<0?999:bi);});}
 if(!inventory.controls.length&&inventory.notes.length>1)inventory.controls.push(...inventory.notes.map((entry,index)=>({kind:'info',label:entry.text.split('\n')[0].slice(0,100)||`Note ${index+1}`,group:entry.title,props:{value:entry.text,description:entry.text}})));
 const controls=inventory.controls,count=Math.max(1,Math.ceil(controls.length/pageSize)),page=Math.min(pages[key]||0,count-1);
 const meta=STUDIO_TABS.find(x=>x[0]===tab)||STUDIO_TABS[0];
 const title=meta[1];
 const close=()=>{setOverlay(null);const view=frameRef.current?.ownerDocument.defaultView;view?.requestAnimationFrame(()=>{if(returnFocus.current?.isConnected)returnFocus.current.focus({preventScroll:true});else studioFocusable(frameRef.current)[0]?.focus({preventScroll:true});});};
 const open=model=>{returnFocus.current=frameRef.current?.ownerDocument.activeElement;setOverlay(model);};
 const changePage=direction=>{if(overlay){overlayPage.current?.(direction);return;}setPages(prev=>({...prev,[key]:clampNumber(page+direction,0,count-1)}));};
 const changeTab=direction=>{if(busy||overlay)return;const idx=STUDIO_TABS.findIndex(x=>x[0]===tab);setTab(STUDIO_TABS[(idx+direction+STUDIO_TABS.length)%STUDIO_TABS.length][0]);};
 useStudioInput(frameRef,cursorRef,{page:changePage,back:()=>overlay?close():exitStudio()});
 useEffect(()=>{const el=frameRef.current,view=el?.ownerDocument.defaultView;if(!el||!view)return;const measure=()=>setSize({width:el.clientWidth,height:el.clientHeight});measure();let observer;try{observer=new view.ResizeObserver(measure);observer.observe(el);}catch{}view.addEventListener('resize',measure);return()=>{observer?.disconnect();view.removeEventListener('resize',measure);};},[]);
 useEffect(()=>{if(previousKey.current===key)return;previousKey.current=key;setOverlay(null);const frame=frameRef.current;if(frame&&!frame.contains(frame.ownerDocument.activeElement))studioFocusable(frame)[0]?.focus({preventScroll:true});},[key]);
 useEffect(()=>{const frame=frameRef.current,doc=frame?.ownerDocument;if(!frame||overlay||doc.querySelector('[data-df-owned-dialog]'))return;if(!frame.contains(doc.activeElement)){const grid=frame.querySelector('[data-df-controls]');studioFocusable(grid||frame)[0]?.focus({preventScroll:true});}},[key,page,pageSize,controls.map(x=>x.label).join('|'),overlay]);
 const navEvent=e=>{const code=e.detail?.button;if([5,6,7,8].includes(code)){e.stopPropagation();e.preventDefault?.();if(code===5||code===6)changeTab(code===5?-1:1);else changePage(code===7?-1:1);}else if(code===2&&overlay){e.stopPropagation();close();}};
 const pageTitle=index=>controls[index*pageSize]?.label||'Overview';
 const notesText=inventory.notes.map((x,i)=>`${String(i+1).padStart(2,'0')} / ${x.warning?'COMPATIBILITY':'INFORMATION'}\n${x.text}`).join('\n\n');
 return h(U.Focusable,{ref:frameRef,'data-df-frame':true,'data-df-studio':true,'data-short':short,'data-narrow':narrow,'data-motion':motion,className:'df-studio',style:{height:frameHeight},onButtonDown:navEvent,onCancel:e=>{e?.stopPropagation?.();if(overlay)close();else exitStudio();},'flow-children':'column'},h('style',null,studioCSS),h('div',{className:'df-atmosphere'}),
  h('header',{className:'df-top'},h('div',{className:'df-brand'},h('span',{className:'df-logo'},studioIcon('fusion',23)),'Deck Fusion'),h('span',{className:'df-beta'},'v0.3-beta5'),h('div',{className:'df-game'},h('span',{className:'df-eyebrow'},'Active game'),h('strong',{title:p?.name},p?.name||'Select a game'),h('span',{className:dirty?'df-dirty':'df-eyebrow'},dirty?'● Unapplied changes':'Saved configuration')),
   h(StudioButton,{className:'df-icon df-motion-control',onClick:()=>{const next=!motion;setMotion(next);try{sessionStorage.setItem('deck-fusion-motion',next?'on':'off');}catch{}},'aria-label':motion?'Pause interface animation':'Enable interface animation'},studioIcon('spark',16)),
   h(StudioButton,{className:'df-primary',disabled:busy||!p,onClick:onApply},studioIcon('check',16),narrow?'Apply':'Review & apply'),h(StudioButton,{className:'df-icon',onClick:()=>exitStudio(),'aria-label':'Back to Steam'},studioIcon('close',18))),
  h('div',{className:'df-body'},h('nav',{className:'df-nav','aria-label':'Configuration tabs'},h('div',{className:'df-eyebrow df-nav-label'},'Expert Mode'),...STUDIO_TABS.map(([id,label,icon])=>h(StudioButton,{key:id,className:'df-nav-button','data-active':tab===id,'aria-label':label,'aria-current':tab===id?'page':undefined,disabled:busy,onClick:()=>setTab(id)},studioIcon(icon,18),h('span',null,label))),null),
   h('main',{className:'df-main'},h('div',{className:'df-hero'},h('div',{className:'df-hero-copy'},h('h1',null,title)),h('div',{className:'df-orbit','aria-hidden':true},h('div',{className:'df-ring'}),h('div',{className:'df-ring'}),h('div',{className:'df-ring'}),h('div',{className:'df-orb'},studioIcon(meta[2],30)),h('div',{className:'df-metric'},p?.lsfg.enabled&&p.base_fps?`${p.base_fps} → ${p.base_fps*p.lsfg.multiplier} FPS target`:'Per-game settings'))),
    h('div',{className:'df-toolbar'},h('span',{className:'df-toolbar-label'},'Controls'),h(StudioButton,{className:'df-page-select',onClick:()=>open({type:'select',title:'Jump to settings page',value:page,options:Array.from({length:count},(_,i)=>({label:`${String(i+1).padStart(2,'0')}  ${pageTitle(i)}`,data:i})),choose:x=>setPages(prev=>({...prev,[key]:x.data}))})},h('span',null,`${String(page+1).padStart(2,'0')} / ${pageTitle(page)}`),studioIcon('arrow',14))),
    h('div',{className:'df-grid','data-df-controls':tab},...controls.slice(page*pageSize,(page+1)*pageSize).map(item=>h(StudioField,{key:item.label,item,open,disabled:busy})),!controls.length&&h('div',{className:'df-empty'},inventory.notes[0]?.text||'Select a game in Library to get started.')),
    h('div',{className:'df-pagination'},h(StudioButton,{className:'df-icon',disabled:page===0,onClick:()=>changePage(-1),'aria-label':'Previous settings page'},studioIcon('back',16)),h('span',{className:'df-page-count','aria-live':'polite'},`${page+1} / ${count}`),h('div',{className:'df-dots','aria-hidden':true},...Array.from({length:Math.min(count,7)},(_,i)=>h('span',{key:i,className:'df-dot','data-active':i===Math.min(page,6)}))),inventory.notes.length>0&&h(StudioButton,{className:'df-notes','data-warning':inventory.notes.some(x=>x.warning),onClick:()=>open({type:'reader',title:'Notes & compatibility',text:notesText})},studioIcon('info',14),`${inventory.notes.length} notes`),h(StudioButton,{className:'df-icon',disabled:page>=count-1,onClick:()=>changePage(1),'aria-label':'Next settings page'},studioIcon('arrow',16))),
    null)),
  h('footer',{className:'df-footer'},h('span',null,h('b',{className:'df-key'},'L1 R1'),'Tabs'),h('span',null,'Previous / Next pages'),h('span',null,h('b',{className:'df-key'},'A'),'Select'),h('span',null,'Mouse / touch · Right pad · R2 click'),h(StudioButton,{className:'df-status',role:error?'alert':'status','data-error':!!error,onClick:()=>open({type:'reader',title:error?'Operation needs attention':'Status',text:error||message||'Ready'})},error||message||'Ready'),runtimeJob&&h(StudioButton,{onClick:cancelRuntime},'Cancel operation')),
  progress!==null&&h('progress',{className:'df-progress',max:1,value:progress,'aria-label':'Operation progress'}),
  overlay&&h(StudioOverlay,{key:overlay.title||overlay.item?.label,model:overlay,close,short,narrow,pageRef:overlayPage}),h('div',{ref:cursorRef,className:'df-cursor','aria-hidden':true},h('svg',{width:22,height:26,viewBox:'0 0 22 26'},h('path',{d:'M2 1v21l6-6 5 9 4-2-5-9h8z',fill:'white',stroke:'#172233',strokeWidth:1.4}))));
}
