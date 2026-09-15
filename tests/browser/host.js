/* Inspection host only. Real React 18; simulated Decky widgets and Steam API.
 * Never included in the runtime entry point. No GPU/Proton/Decky validation.
 */
const registry={},instances={};
for(const chunk of self.webpackChunk_jupyterlab_application_top)Object.assign(registry,chunk[1]);
function req(id){if(id===44914)return req(96540);if(instances[id])return instances[id].exports;const m={exports:{}};instances[id]=m;registry[id](m,m.exports,req);return m.exports;}
window.SP_REACT=req(96540);window.ReactDOM=req(40961);
const R=SP_REACT,h=R.createElement;
const AppRoot=ReactDOM.createRoot(document.getElementById('app')), ModalRoot=ReactDOM.createRoot(document.getElementById('modals'));
const desc=p=>p.description&&h('div',{className:'description'},p.description);
const frame=(p,control)=>h('div',{className:'field'},h('div',{className:'fieldline'},h('label',null,p.label),control),desc(p));
const navs={}, steam={},listeners={};
window.calls=[];
window.SteamClient={Apps:{RegisterForAppDetails(id,callback){(listeners[id]??=[]).push(callback);callback({strLaunchOptions:steam[id]??'--skip-launcher'});return {unregister(){listeners[id]=listeners[id].filter(x=>x!==callback);}}},SetAppLaunchOptions(id,value){steam[id]=value;window.calls.push({steam_write:value});for(const cb of listeners[id]||[])cb({strLaunchOptions:value});}}};
window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit={connect(){return {call:async (...args)=>{window.calls.push(args);return await window.pycall({method:args[0],args:args.slice(1)});},routerHook:{addRoute:(path,c)=>navs[path]=c,removeRoute:path=>delete navs[path]}}}};
window.DFL={
 PanelSection:p=>h('section',null,h('h2',null,p.title),p.children),PanelSectionRow:p=>h('div',{className:'row'},p.children),
 ButtonItem:p=>h('div',null,h('button',{onClick:p.onClick,disabled:p.disabled,style:p.style},p.children),desc(p)),
 DialogButton:p=>h('button',{onClick:p.onClick,disabled:p.disabled,style:p.style},p.children),
 ToggleField:p=>frame(p,h('input',{'aria-label':p.label,type:'checkbox',checked:p.checked,onChange:e=>p.onChange(e.target.checked),disabled:p.disabled})),
 TextField:p=>frame(p,h('input',{'aria-label':p.label,value:p.value,onChange:p.onChange,disabled:p.disabled})),
 DropdownItem:p=>frame(p,h('select',{'aria-label':p.label,value:p.selectedOption??'',disabled:p.disabled,onChange:e=>p.onChange(p.rgOptions.find(x=>String(x.data)===e.target.value))},h('option',{value:'',disabled:true},'Select…'),p.rgOptions.map(x=>h('option',{value:x.data,key:x.data},x.label)))),
 SliderField:p=>frame(p,h('div',{className:'slider'},h('input',{'aria-label':p.label,type:'range',min:p.min,max:p.max,step:p.step,value:p.value,onChange:e=>p.onChange(Number(e.target.value))}),h('span',null,p.value))),
 Focusable:p=>h('div',{tabIndex:0,style:p.style,onFocus:p.onFocus},p.children),
 Tabs:p=>h('div',{className:'tabs'},h('nav',null,p.tabs.map(x=>h('button',{key:x.id,'data-active':x.id===p.activeTab,onClick:()=>p.onShowTab(x.id)},x.title))),h('div',{className:'tabbody'},p.tabs.find(x=>x.id===p.activeTab)?.content)),
 ConfirmModal:p=>h('div',{className:'overlay'},h('div',{className:'dialog',role:'dialog','aria-modal':true},h('h2',null,p.strTitle),h('p',null,p.strDescription),p.children,h('div',{className:'actions'},h('button',{onClick:p.onCancel},p.strCancelButtonText),h('button',{disabled:p.bOKDisabled,onClick:p.onOK},p.strOKButtonText)))),
 showModal(element){const close=()=>ModalRoot.render(null);ModalRoot.render(R.cloneElement(element,{closeModal:close}));return {Close:close};},
 Navigation:{Navigate:path=>AppRoot.render(h(navs[path])),CloseSideMenus(){}},staticClasses:{}
};
window.startApp=async()=>{const mod=await import(window.bundleURL||'/dist/index.js');window.plugin=mod.default();AppRoot.render(h(navs['/deck-fusion']));};
