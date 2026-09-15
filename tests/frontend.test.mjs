import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('self-contained bundle loads and registers guided, expert and compatibility entry routes', async()=>{
  const routes=new Map();
  globalThis.window=globalThis;
  globalThis.SP_REACT={Component:class {},createElement:(type,props,...children)=>({type,props,children}),useState(){},useEffect(){},useRef(){}};
  const navigation=[];
  globalThis.DFL={staticClasses:{Title:'Title'},Navigation:{Navigate:path=>navigation.push(path),CloseSideMenus(){}}};
  globalThis.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit={connect:()=>({routerHook:{addRoute:(key,value)=>routes.set(key,value),removeRoute:key=>routes.delete(key)}})};
  const source=await readFile(new URL('../dist/index.js',import.meta.url),'utf8');
  assert.doesNotMatch(source,/^import\s/m,'No unresolved package or source imports');
  const {default:factory}=await import('../dist/index.js');
  const plugin=factory();
  assert.equal(plugin.name,'Deck Fusion');
  assert.deepEqual([...routes.keys()],['/deck-fusion','/deck-fusion/expert','/deck-fusion/setup']);
  const text=node=>typeof node==='string'?node:(node?.children||[]).map(text).join('|');
  const sidebar=plugin.content.type();
  assert.match(text(sidebar),/Open Deck Fusion/);assert.doesNotMatch(text(sidebar),/Expert Mode|Set up a game/);
  sidebar.children[0].children[0].props.onClick();
  assert.deepEqual(navigation,['/deck-fusion']);
  assert.equal(routes.get('/deck-fusion')().children[0].props.startWizard,true);
  assert.notEqual(routes.get('/deck-fusion/expert')().children[0].props?.startWizard,true);
  plugin.onDismount();assert.equal(routes.size,0);
});
