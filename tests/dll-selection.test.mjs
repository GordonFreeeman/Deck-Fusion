import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../dist/index.js',import.meta.url),'utf8');
const isolated=source.slice(source.indexOf('function customEntries('),source.indexOf('const commonProxyNames='));
const context=vm.createContext({});vm.runInContext(isolated,context);
const obj=s=>JSON.parse(JSON.stringify(context.customEntries(s)));
test('normalizes comma-separated DLL basenames and deduplicates',()=>{
 assert.deepEqual(Array.from(context.moduleNames('DXGI.dll, Version, winmm.dll, dxgi')),['dxgi','version','winmm']);
});
test('batch addition keeps previous entries and their custom orders',()=>{
 const result=context.mergeCustomModules('version=b,n;dinput8=',context.moduleNames('dxgi,version,winmm'),'n,b',true);
 assert.deepEqual(obj(result),{version:'b,n',dinput8:'',dxgi:'n,b',winmm:'n,b'});
});
test('manual multiple names update only explicitly named modules',()=>{
 const result=context.mergeCustomModules('version=b;other=n',context.moduleNames('dxgi,version,winmm'),'n,b');
 assert.deepEqual(obj(result),{version:'n,b',other:'n',dxgi:'n,b',winmm:'n,b'});
});
test('repeated batches are cumulative, not single-value replacement',()=>{
 let value='';for(const input of ['dxgi','version','winmm'])value=context.mergeCustomModules(value,context.moduleNames(input),'n,b',true);
 assert.deepEqual(obj(value),{dxgi:'n,b',version:'n,b',winmm:'n,b'});
});
test('blank names, paths, injections and double dots are rejected',()=>{
 for(const value of ['','version,','/tmp/x.dll','../version','a/b','a\\b','a..b','$(id)','version=n,b'])assert.throws(()=>context.moduleNames(value));
});
