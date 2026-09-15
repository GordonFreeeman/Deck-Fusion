import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
const source=readFileSync(new URL('../dist/index.js',import.meta.url),'utf8').replace('export default function(){','function pluginFactory(){');
function host(){
 const effects=[],heights=[];
 const sandbox={console,SP_REACT:{Component:class {},createElement(){},useRef(){},useEffect:fn=>effects.push(fn),useState:initial=>[initial,value=>heights.push(typeof value==='function'?value(heights.at(-1)??initial):value)]},DFL:{}};
 sandbox.window=sandbox;
 sandbox.innerHeight=0;
 sandbox.ResizeObserver=class{constructor(){throw Error('Module-window observer must not be used');}};
 sandbox.requestAnimationFrame=()=>{throw Error('Module-window scheduler must not be used');};
 sandbox.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit={connect:()=>({})};
 vm.createContext(sandbox);vm.runInContext(source,sandbox);
 return {sandbox,effects,heights};
}
function element({height=800,top=40,scale=1}={}){
 const view={innerHeight:height,visualViewport:{height,offsetTop:0}};
 const node={ownerDocument:{defaultView:view,documentElement:{clientHeight:height}},isConnected:true,offsetHeight:688,getBoundingClientRect:()=>({top,width:1280*scale,height:688*scale})};
 return node;
}

test('reads visible owner window while module window height is zero',()=>{
 const {sandbox:s}=host();assert.equal(s.steamFrameHeight(element()),688);
});
test('uses the owner document viewport fallback',()=>{
 const {sandbox:s}=host(),node=element();node.ownerDocument.defaultView.innerHeight=0;
 assert.equal(s.steamFrameHeight(node),688);
});
test('retains footer clearance for scaled Steam UI',()=>{
 const {sandbox:s}=host();assert.equal(s.steamFrameHeight(element({height:1000,top:50,scale:1.25})),688);
});
test('ignores transitional zero visualViewport dimensions',()=>{
 const {sandbox:s}=host(),node=element();node.ownerDocument.defaultView.visualViewport.height=0;
 assert.equal(s.steamFrameHeight(node),688);
});
test('invalid, offscreen, detached and hidden geometry never commits zero',()=>{
 const {sandbox:s}=host();
 for(const change of [n=>n.isConnected=false,n=>n.ownerDocument.defaultView=null,n=>n.getBoundingClientRect=()=>({top:900,width:1280,height:688}),n=>n.getBoundingClientRect=()=>({top:40,width:0,height:0}),n=>n.getBoundingClientRect=()=>({top:NaN,width:1280,height:688}),n=>n.getBoundingClientRect=()=>{throw Error('detached')},n=>{n.ownerDocument.defaultView.innerHeight=0;n.ownerDocument.documentElement.clientHeight=0;}]){
  const node=element();change(node);assert.equal(s.steamFrameHeight(node),null);
 }
});
test('schedules and listens in owner window; missing observer is nonfatal; cleans up',()=>{
 const {sandbox:s,effects,heights}=host(),node=element(),view=node.ownerDocument.defaultView;
 const callbacks=new Map(),events=new Map();let next=0,cancelled=null;
 view.requestAnimationFrame=callback=>{callbacks.set(++next,callback);return next;};view.cancelAnimationFrame=id=>{cancelled=id;callbacks.delete(id);};
 view.addEventListener=(type,callback)=>events.set(type,callback);view.removeEventListener=type=>events.delete(type);
 view.ResizeObserver=class{constructor(){throw Error('Host observer unavailable');}};
 const fallback=s.useSteamViewport({current:node});assert.match(fallback,/calc\(100vh/);
 const cleanup=effects[0]();assert.equal(heights.at(-1),688);assert.ok(events.has('resize'));
 view.innerHeight=640;view.visualViewport.height=640;events.get('resize')();callbacks.get(next)();assert.equal(heights.at(-1),528);
 events.get('resize')();cleanup();assert.equal(cancelled,next);assert.equal(events.size,0);
});
test('focus scrolling changes only the pane and works without a same-realm HTMLElement',()=>{
 const {sandbox:s}=host();
 const target={getBoundingClientRect:()=>({top:550,bottom:600})};
 const pane={offsetHeight:400,scrollTop:0,contains:t=>t===target,getBoundingClientRect:()=>({top:100,bottom:500,height:400})};
 s.scrollFocusedControl({target,currentTarget:pane});assert.equal(pane.scrollTop,114);
 s.scrollFocusedControl({});assert.equal(pane.scrollTop,114);
});

// Steam can mount a custom route at y=0 beneath its persistent header.
test('reserves Steam header space at zero origin and avoids double insets on positioned routes',()=>{
 for(const [top,scale,expected] of [[0,1,'48px'],[40,1,'8px'],[60,1,'0px'],[50,1.25,'8px']]){
  const {sandbox:s,effects}=host(),node=element({top,scale}),styles=new Map();node.style={setProperty:(k,v)=>styles.set(k,v)};
  s.useSteamViewport({current:node});const cleanup=effects[0]();assert.equal(styles.get('--df-safe-top'),expected);cleanup();
 }
});
