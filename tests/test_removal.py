from pathlib import Path
import json
import struct
import pytest
from conftest import pe_bytes
from fusion_removal import GraphicsRemoval, remove_overrides
from fusion_identity import version_strings, identify
from fusion_transaction import Transaction
from fusion_util import FusionError, atomic_json


def ctx(packages):
 e,p,root,exe=packages
 return e,p,root,exe,GraphicsRemoval(e),{'appid':p['appid'],'exe':str(exe),'launch':'%command% --skip-launcher'}


def commit(e,m,payload):
 plan=m.plan(payload);assert not plan['blockers'];stage=m.prepare({**payload,'approval':plan['approval_token']})
 e.finish(payload['appid'],stage['token'],stage['launch_after'])
 return stage


def test_unmanaged_injectors_removed_unknowns_presets_and_shared_sdk_kept_and_undo(packages):
 e,p,root,exe,m,payload=ctx(packages);folder=exe.parent
 status=e.packages.status()
 opt=Path(status['opti']['path'])/'OptiScaler.dll';resh=Path(status['reshade']['path'])/'ReShade64.dll'
 (folder/'winmm.dll').write_bytes(opt.read_bytes());(folder/'ReShade64.dll').write_bytes(resh.read_bytes())
 untouched={'version.dll':b'original game dll','ReShade.ini':b'user preset','amd_fidelityfx_dx12.dll':b'shared sdk'}
 for name,data in untouched.items():(folder/name).write_bytes(data)
 (folder/'reshade-shaders').mkdir();(folder/'reshade-shaders/user.fx').write_bytes(b'shared shader')
 payload['launch']='WINEDLLOVERRIDES="version,winmm=n,b;foo=n" %command% --skip-launcher'
 before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
 plan=m.plan(payload);assert plan['file_count']==2 and plan['can_apply'];assert 'version' in plan['launch_after'] and 'winmm' not in plan['launch_after']
 assert all((root/n).read_bytes()==data for n,data in before.items()),'Preview writes nothing'
 stage=commit(e,m,payload)
 assert not (folder/'winmm.dll').exists() and not (folder/'ReShade64.dll').exists()
 for name,data in untouched.items():assert (folder/name).read_bytes()==data
 assert (folder/'reshade-shaders/user.fx').read_bytes()==b'shared shader'
 undo=commit(e,m,{**payload,'launch':stage['launch_after'],'undo':True})
 assert undo['launch_after']==payload['launch']
 assert all((root/n).read_bytes()==data for n,data in before.items())


def install_managed(packages):
 e,p,root,exe=packages;p['opti']['enabled']=True;p['lsfg']['enabled']=True
 p['base_fps']=30;p['api']='dx11';p['backup_conflicts']=True
 review=e.review(p,'%command%');desired,extras,_=e.build(review['profile'])
 (exe.parent/'dxgi.dll').write_bytes(b'original game dll')
 stage=Transaction(root,e.store(p['appid'])).prepare(desired,extras,'%command%',review['launch_after'],True);e.finish(p['appid'],stage['token'],stage['launch_after'])
 return e,p,root,exe,GraphicsRemoval(e),{'appid':p['appid'],'exe':str(exe),'launch':stage['launch_after']}


def test_managed_originals_restored_lsfg_preserved_and_edited_files_kept(packages):
 e,p,root,exe,m,payload=install_managed(packages)
 config=exe.parent/'OptiScaler.ini';config.write_text('user edited configuration')
 stage=commit(e,m,payload)
 assert (exe.parent/'dxgi.dll').read_bytes()==b'original game dll'
 assert config.read_text()=='user edited configuration'
 saved=e.profile(p['appid']);assert not saved['opti']['enabled'] and saved['lsfg']['enabled'] and saved['base_fps']==30
 assert str(e.wrapper) in stage['launch_after']
 runtime=json.loads((e.store(p['appid'])/'runtime.json').read_text());assert runtime['lsfg']['enabled'] and not runtime['opti_enabled'] and not runtime['dll_overrides']
 assert Transaction(root,e.store(p['appid'])).manifest()['files']=={}


def test_changed_unknown_managed_dll_is_not_removed_or_overwritten(packages):
 e,p,root,exe,m,payload=install_managed(packages)
 (exe.parent/'dxgi.dll').write_bytes(b'game update replaced this')
 commit(e,m,payload)
 assert (exe.parent/'dxgi.dll').read_bytes()==b'game update replaced this'


@pytest.mark.parametrize('damage',['file','launch','snapshot'])
def test_undo_refuses_to_overwrite_later_changes_or_damaged_backups(packages,damage):
 e,p,root,exe,m,payload=install_managed(packages);stage=commit(e,m,payload)
 undo={**payload,'launch':stage['launch_after'],'undo':True}
 if damage=='file':(exe.parent/'dxgi.dll').write_bytes(b'updated game file')
 elif damage=='launch':undo['launch']+=' --user-edit'
 else:
  receipt=json.loads((Path(stage['backup'])/'receipt.json').read_text())
  a=next(x for x in receipt['actions'] if x['area']=='game' and x['before']);(Path(stage['backup'])/a['before']).write_bytes(b'broken')
 with pytest.raises(FusionError,match='changed|damaged'):m.plan(undo)
 if damage=='file':assert (exe.parent/'dxgi.dll').read_bytes()==b'updated game file'


@pytest.mark.parametrize('change',['file','record','running'])
def test_stale_approval_and_newly_running_game_cannot_remove_files(packages,monkeypatch,change):
 e,p,root,exe,m,payload=install_managed(packages);plan=m.plan(payload)
 if change=='file':(exe.parent/'dxgi.dll').write_bytes(b'independent file')
 elif change=='record':atomic_json(e.store(p['appid'])/'runtime.json',{'custom':'edit'})
 else:monkeypatch.setattr(m,'idle',lambda _:(_ for _ in ()).throw(FusionError('Game running')))
 before=(exe.parent/'dxgi.dll').read_bytes()
 with pytest.raises(FusionError,match='changed|running'):m.prepare({**payload,'approval':plan['approval_token']})
 assert (exe.parent/'dxgi.dll').read_bytes()==before


def test_interrupted_removal_rolls_back_and_existing_journal_is_recoverable(packages):
 e,p,root,exe,m,payload=install_managed(packages);before=(exe.parent/'dxgi.dll').read_bytes();plan=m.plan(payload)
 def fail(*_):raise OSError('simulated disk failure')
 with pytest.raises(OSError):m.prepare({**payload,'approval':plan['approval_token']},fail)
 assert (exe.parent/'dxgi.dll').read_bytes()==before
 stage=m.prepare({**payload,'approval':plan['approval_token']})
 tx=Transaction(root,e.store(p['appid']));assert tx.pending()
 result=e.rollback(p['appid'],stage['token']);assert result['launch_options']==payload['launch']
 assert (exe.parent/'dxgi.dll').read_bytes()==before


def test_linked_dlls_and_case_duplicates_stay_untouched(packages,tmp_path):
 e,p,root,exe,m,payload=ctx(packages)
 external=tmp_path/'other.dll';external.write_bytes(b'other mod');(exe.parent/'version.dll').symlink_to(external)
 opt=(Path(e.packages.status()['opti']['path'])/'OptiScaler.dll').read_bytes()
 (exe.parent/'winmm.dll').write_bytes(opt);(exe.parent/'WINMM.dll').write_bytes(b'unknown')
 plan=m.plan(payload)
 assert plan['file_count']==0 and all(x['action']=='keep' for x in plan['files'])
 assert external.read_bytes()==b'other mod'


def version_pe(product='OptiScaler',original='OptiScaler.dll'):
 def block(key,value=b'',kind=0,children=b''):
  key=(key+'\0').encode('utf-16le');header=struct.pack('<HHH',0,len(value)//2 if kind else len(value),kind)+key
  header+=b'\0'*(-len(header)%4);body=header+value;body+=b'\0'*(-len(body)%4);body+=children
  return struct.pack('<H',len(body))+body[2:]
 def string(k,v):return block(k,(v+'\0').encode('utf-16le'),1)
 values=string('ProductName',product)+string('OriginalFilename',original)
 version=block('VS_VERSION_INFO',b'\0'*52,0,block('StringFileInfo',children=block('040904b0',children=values)))
 data=bytearray(pe_bytes(api=None));struct.pack_into('<H',data,0x80+22,0x2000)
 struct.pack_into('<II',data,0x80+24+112+16,0x1000,1024)
 # Resource type 16 -> name 1 -> language 1033 -> data entry.
 for off,name,dest in [(0,16,0x80000020),(0x20,1,0x80000040),(0x40,1033,0x60)]:
  struct.pack_into('<HH',data,0x400+off+12,0,1);struct.pack_into('<II',data,0x400+off+16,name,dest)
 struct.pack_into('<IIII',data,0x460,0x1100,len(version),0,0);data[0x500:0x500+len(version)]=version
 return data


@pytest.mark.parametrize('product,original,label',[('OptiScaler','OptiScaler.dll','OptiScaler'),('ReShade','ReShade64.dll','ReShade'),('Game','version.dll',None)])
def test_structured_version_identity_not_loose_strings(tmp_path,product,original,label):
 p=tmp_path/'version.dll';p.write_bytes(version_pe(product,original));assert identify(p)[0]==label
 p.write_bytes(pe_bytes()+b'OptiScaler\0ReShade\0'+ 'OptiScaler.dll'.encode('utf-16le'));assert identify(p)==(None,None)


def test_expanded_or_compound_override_is_not_rewritten():
 assert remove_overrides('WINEDLLOVERRIDES="version,winmm=n,b;foo=n" %command% --foo',{'winmm'})=="WINEDLLOVERRIDES='version=n,b;foo=n' %command% --foo"
 with pytest.raises(FusionError):remove_overrides('WINEDLLOVERRIDES="$OLD;winmm=n,b" %command%',{'winmm'})
 with pytest.raises(FusionError):remove_overrides('WINEDLLOVERRIDES="winmm=n,b" %command% && echo hi',{'winmm'})


def test_managed_missing_files_restore_original_and_keep_its_permissions(packages):
 e,p,root,exe,m,payload=install_managed(packages)
 dll=exe.parent/'dxgi.dll';dll.unlink()
 store=e.store(p['appid']);manifest=json.loads((store/'manifest.json').read_text())
 manifest['files'][str(dll.relative_to(root))]['mode']=0o640;atomic_json(store/'manifest.json',manifest)
 commit(e,m,payload)
 assert dll.read_bytes()==b'original game dll' and dll.stat().st_mode&0o777==0o640


def test_native_only_or_unreadable_prefix_override_blocks_removal(packages,monkeypatch):
 e,p,root,exe,m,payload=ctx(packages)
 (exe.parent/'winmm.dll').write_bytes((Path(e.packages.status()['opti']['path'])/'OptiScaler.dll').read_bytes())
 monkeypatch.setattr('fusion_removal.inspect_overrides',lambda *_:{'registry':[{'name':'winmm','order':'n'}],'warnings':[]})
 with pytest.raises(FusionError,match='native-only'):m.plan(payload)
 monkeypatch.setattr('fusion_removal.inspect_overrides',lambda *_:{'registry':[],'warnings':['user.reg exceeds read limit; not fully inspected.']})
 with pytest.raises(FusionError,match='Cannot verify'):m.plan(payload)
 assert (exe.parent/'winmm.dll').exists()


def test_edited_files_and_protected_same_loader_prevent_unrelated_override_cleanup(packages):
 e,p,root,exe,m,payload=ctx(packages)
 (exe.parent/'winmm.dll').write_bytes((Path(e.packages.status()['opti']['path'])/'OptiScaler.dll').read_bytes())
 (root/'winmm.dll').write_bytes(b'game dll in another directory')
 payload['launch']='WINEDLLOVERRIDES="winmm=n,b;other=n" %command% --flag'
 result=m.plan(payload);assert result['launch_after']==payload['launch']
 commit(e,m,payload);assert (root/'winmm.dll').read_bytes()==b'game dll in another directory'


def test_staging_race_aborts_before_changes_and_failed_finish_can_roll_back(packages,monkeypatch):
 e,p,root,exe,m,payload=install_managed(packages)
 dll=exe.parent/'dxgi.dll';before=dll.read_bytes();plan=m.plan(payload)
 real=Transaction._stage;changed=False
 def race(self,*args,**kwargs):
  nonlocal changed
  real(self,*args,**kwargs)
  if not changed: changed=True;atomic_json(e.store(p['appid'])/'runtime.json',{'independent':'edit'})
 monkeypatch.setattr(Transaction,'_stage',race)
 with pytest.raises(FusionError,match='changed'):m.prepare({**payload,'approval':plan['approval_token']})
 assert dll.read_bytes()==before and not Transaction(root,e.store(p['appid'])).pending()
 monkeypatch.setattr(Transaction,'_stage',real)
 plan=m.plan(payload);stage=m.prepare({**payload,'approval':plan['approval_token']})
 with pytest.raises(FusionError,match='not verified'):e.finish(p['appid'],stage['token'],'changed launch')
 e.rollback(p['appid'],stage['token']);assert dll.read_bytes()==before
