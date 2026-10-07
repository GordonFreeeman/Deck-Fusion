from pathlib import Path
import copy
import pytest
from fusion_engine import migrate_profile
from fusion_opti_editor import parse_manual
from fusion_transaction import Transaction
from fusion_util import FusionError


def configured(packages):
 e,p,root,exe=packages;p['opti']['enabled']=True;p['api']='dx11';p['lsfg']['enabled']=False
 return e,p,root,exe


def test_preview_and_save_are_read_only_and_manual_values_survive_apply(packages):
 e,p,root,exe=configured(packages)
 before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
 model=e.opti_editor(p);text=model['text'].replace('Dx11Upscaler=fsr31','Dx11Upscaler=xess').replace('Sharpness=auto','Sharpness=0.25')+'\n[Hotfix]\nSkipDxgiLoad=true\nDisableOverlays=false\n'
 edited=e.opti_manual(p,text)
 assert p['opti']['manual_ini']=='' and edited['opti']['dx11']=='xess'
 assert edited['opti']['steam_input']=='keep'
 assert before=={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
 stage=e.prepare(edited,'%command%');e.finish(p['appid'],stage['token'],stage['launch_after'])
 actual=(exe.parent/'OptiScaler.ini').read_text()
 assert 'Dx11Upscaler=xess' in actual and 'Sharpness=0.25' in actual and 'SkipDxgiLoad=true' in actual
 saved=e.profile(p['appid']);assert saved['opti']['manual_ini']==text
 # Changing a high-level value cannot quietly overwrite a manual INI.
 saved['opti']['dx11']='fsr31'
 plan=e.plan(saved,stage['launch_after']);assert not plan['blockers']
 assert plan['profile']['opti']['dx11']=='xess'
 desired,_,_=e.build(e.validate(saved,stage['launch_after']))
 assert b'Dx11Upscaler=xess' in next(v for n,v in desired.items() if n.endswith('OptiScaler.ini'))
 reset=e.opti_manual(saved,'');repair=e.prepare(reset,stage['launch_after'])
 e.finish(p['appid'],repair['token'],repair['launch_after'])
 actual=(exe.parent/'OptiScaler.ini').read_text()
 assert 'Sharpness=auto' in actual and 'SkipDxgiLoad' not in actual
 assert not e.profile(p['appid'])['opti']['manual_reset']


def test_loading_installed_config_and_resetting_are_read_only(packages):
 e,p,root,exe=configured(packages)
 text=e.opti_editor(p)['text'].replace('Sharpness=auto','Sharpness=0.9')
 (exe.parent/'OptiScaler.ini').write_text(text)
 model=e.opti_editor(p);assert model['installed']==text and not model['manual']
 edited=e.opti_manual(p,text)
 reset=e.opti_manual(edited,'');assert reset['opti']['manual_ini']=='' and reset['opti']['overrides']=={}
 assert 'Sharpness=auto' in e.opti_ini(reset,False)
 assert (exe.parent/'OptiScaler.ini').read_text()==text


def test_manual_config_keeps_reshade_chaining_and_original_backup(packages):
 e,p,root,exe=configured(packages);p['reshade']['mode']='opti'
 text=e.opti_editor(p)['text'].replace('LoadReshade=true','LoadReshade=false')
 original=e.opti_editor(p)['text'];(exe.parent/'OptiScaler.ini').write_text(original)
 edited=e.opti_manual(p,text)
 desired,_,_=e.build(e.validate(edited));assert b'LoadReshade=true' in next(v for n,v in desired.items() if n.endswith('OptiScaler.ini'))
 plan=e.plan(edited,'%command%');assert not plan['blockers']
 stage=e.prepare_approved(edited,'%command%',plan['approval_token']);e.finish(p['appid'],stage['token'],stage['launch_after'])
 meta=Transaction(root,e.store(p['appid'])).manifest()['files'][str((exe.parent/'OptiScaler.ini').relative_to(root))]
 assert meta['before'] and (e.store(p['appid'])/'originals'/meta['before']).read_text()==original
 edited['reshade']['mode']='off';assert 'LoadReshade=false' in e.opti_ini(edited)


@pytest.mark.parametrize('alter',[
 lambda s:s.replace('[FrameGen]','[FrameGen]\nEnabled=false'),
 lambda s:s+'\n[UPSCalers]\nDx11Upscaler=xess\n',
 lambda s:s.replace('Enabled=false','Enabled=auto'),
 lambda s:s.replace('Dx11Upscaler=fsr31','Dx11Upscaler=not-supported'),
 lambda s:s.replace('[Upscalers]','[Broken'),
 lambda s:s+'\0',
 lambda s:s+'\n[Hotfix]\nTest=first\n second\n',
 lambda s:s+'\n[DEFAULT]\nKey=true\n',
])
def test_invalid_manual_ini_cannot_be_saved_or_applied(packages,alter):
 e,p,root,exe=configured(packages);text=alter(e.opti_editor(p)['text'])
 with pytest.raises(FusionError):e.opti_manual(p,text)
 assert not (exe.parent/'OptiScaler.ini').exists()


def test_double_fg_and_manual_int8_metadata_are_checked(packages):
 e,p,root,exe=configured(packages);text=e.opti_editor(p)['text']
 p['lsfg']['enabled']=True
 with pytest.raises(FusionError,match='LSFG'):e.opti_manual(p,text.replace('Enabled=false','Enabled=true'))
 # Metadata is derived even if someone supplied a profile directly to RPC.
 raw=copy.deepcopy(p);raw['opti']['manual_ini']=text+'\n[FSR]\nFsr4ForceModel=2\nFsr4EnableWatermark=true\n'
 from fusion_opti_editor import apply_manual
 apply_manual(raw['opti']);assert raw['opti']['fsr_mode']=='fsr4_int8' and raw['opti']['fsr4_watermark']
 assert migrate_profile({'appid':'123'})['opti']['manual_ini']==''


def test_preview_refuses_linked_or_oversized_installed_ini(packages,tmp_path):
 e,p,root,exe=configured(packages);outside=tmp_path/'other.ini';outside.write_text('foreign')
 current=exe.parent/'OptiScaler.ini';current.symlink_to(outside)
 with pytest.raises(FusionError,match='links|leaves'):e.opti_editor(p)
 assert outside.read_text()=='foreign'
 current.unlink();current.write_bytes(b'a'*(1024*1024+1))
 with pytest.raises(FusionError,match='1 MB'):e.opti_editor(p)
