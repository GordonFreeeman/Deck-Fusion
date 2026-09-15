"""Local browser host. Actual React + plugin; simulated Steam/Decky and game files."""
import asyncio,json,threading,os
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from studio_fixture import fixture,BASE
ROOT=Path(__file__).parent
engine,profile,plugin=fixture()
loop=asyncio.new_event_loop();threading.Thread(target=loop.run_forever,daemon=True).start()
class Host(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  url=self.path.split('?')[0]
  if url=='/':
   html=(ROOT/'host.html').read_text().replace('<script type="module">','<script src="/react.js"></script><script src="/react-dom.js"></script><script type="module">')
   html=html.replace("import {r as React,e as ReactDOM} from './react-vendor.js';",'const React=window.React,ReactDOM=window.ReactDOM;')
   html=html.replace("const fixtures=await(await fetch('./fixture.json')).json();", "const fixtures={}; window.pycall=async request=>await(await fetch('/rpc',{method:'POST',body:JSON.stringify(request)})).json();")
   html=html.replace('</script>', '</script>',2)
   pos=html.rfind('</script>')
   html=html[:pos]+"\nconst source=await(await fetch('/dist/index.js')).text();moduleWindow.eval(source.replace('export default function(){','window.__makePlugin=function(){'));window.host.plugin=moduleWindow.__makePlugin();window.launchQuick();window.ready=true;\n"+html[pos:]
   data=html.encode();mime='text/html'
  elif url in ['/react.js','/react-dom.js']:
   package='react' if url=='/react.js' else 'react-dom'
   vendor=Path(os.environ.get('DF_REACT_VENDOR',str(BASE.parent/'browser-tools/node_modules')))
   data=(vendor/package/'umd'/f'{package}.development.js').read_bytes();mime='text/javascript'
  elif url=='/dist/index.js':data=(BASE/'dist/index.js').read_bytes();mime='text/javascript'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_POST(self):
  request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  result=asyncio.run_coroutine_threadsafe(getattr(plugin,request['method'])(*request['args']),loop).result(30)
  data=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
if __name__=='__main__':
 print('Synthetic Deck Fusion browser host: http://127.0.0.1:8765',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8765),Host).serve_forever()
