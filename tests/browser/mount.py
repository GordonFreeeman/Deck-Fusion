from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]

def fixture():
 import sys,tempfile
 sys.path[:0]=[str(BASE/'tests'),str(BASE/'py_modules'),str(BASE)]
 import conftest
 from fusion_util import atomic_json
 directory=Path(tempfile.mkdtemp(prefix='deck-fusion-browser-'))
 engine,p,game,exe=conftest.packages.__wrapped__(conftest.installation.__wrapped__(directory))
 atomic_json(engine.store('123')/'profile.json',p)
 return {'state':{'games':engine.games(),'packages':engine.packages.status(),'legacy_layers':[],'settings':engine.settings(),'bundled':{},'hardware':engine.hardware()},'profile':p,'scan':engine.scan('123'),'schema':engine.schema('123'),'requirements':engine.requirements(p)}

def mount(page,version='current',separate=True,fixtures=None):
 html=(ROOT/'host.html').read_text();html=html.split('<script type="module">')[0]
 page.set_content(html)
 vendor_dir=Path(__import__('os').environ.get('DF_REACT_VENDOR',str(BASE.parent/'browser-tools/node_modules')))
 page.add_script_tag(path=str(vendor_dir/'react/umd/react.development.js'))
 page.add_script_tag(path=str(vendor_dir/'react-dom/umd/react-dom.development.js'))
 page.evaluate('window.__testReact=React; window.__testReactDOM=ReactDOM')
 src=BASE/'dist/index.js'
 if version!='current':raise ValueError('This packaged harness inspects the current ZIP; historical measurements are in evidence/1.1.2.')
 source=src.read_text().replace('export default function(){','window.__makePlugin=function(){')
 script=(ROOT/'host.html').read_text().split('<script type="module">')[1].split('</script>')[0]
 script=script.replace("import {r as React,e as ReactDOM} from './react-vendor.js';",'const React=window.__testReact,ReactDOM=window.__testReactDOM;')
 script=script.replace("const q=new URLSearchParams(location.search), separate=q.get('separate')!=='0';",'const separate=options.separate;')
 script=script.replace("const fixtures=await(await fetch('./fixture.json')).json();",'const fixtures=options.fixtures;')
 script=script+'''
 const store=new Map();Object.defineProperty(moduleWindow,'sessionStorage',{value:{getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v)),removeItem:k=>store.delete(k)},configurable:true});
 moduleWindow.eval(options.source);window.host.plugin=moduleWindow.__makePlugin();window.launchQuick();window.ready=true;
 '''
 page.evaluate('async options=>{'+script+'}',{'separate':separate,'fixtures':fixture() if fixtures is None else fixtures,'source':source})
 page.wait_for_function('window.ready===true')
