import json
import os
import subprocess
from pathlib import Path
import pytest
from fusion_launch import *
from fusion_util import FusionError

@pytest.mark.parametrize('before,expected',[
    ('','%command%'),('--skip-launcher','%command% --skip-launcher'),
    ('FOO=bar --skip-launcher','FOO=bar %command% --skip-launcher'),
    ('FOO="two words" --flag','FOO="two words" %command% --flag'),
    ('env FOO=bar --skip-launcher','env FOO=bar %command% --skip-launcher'),
    ('gamemoderun','gamemoderun %command%'),('mangohud','mangohud %command%'),
    ('%COMMAND% -dx12','%command% -dx12'),('mangohud %command% --skip-launcher','mangohud %command% --skip-launcher')])
def test_template(before,expected): assert command_template(before)==expected

@pytest.mark.parametrize('bad',["'%command%'",'"%command%"','%command% %command%','unknown_launcher --param',"FOO='oops"])
def test_ambiguous(bad):
    with pytest.raises(FusionError):command_template(bad)

@pytest.mark.parametrize('before',['','--skip-launcher','FOO="a b" %command% --flag','gamemoderun %command%'])
def test_compose_idempotent_and_restore(before):
    path=Path('/home/test/.local/share/deck-fusion/bin/launch')
    after=compose_launch(before,path,'123')
    assert after.count('%command%')==1
    assert compose_launch(after,path,'123')==after
    assert restore_launch(after,after,before,path,'123')==before
    assert '--new-argument' in restore_launch(after+' --new-argument',after,before,path,'123')
    assert str(path) not in restore_launch(after+' --new-argument',after,before,path,'123')


def test_quoted_wrapper():
    p=Path('/home/a b/.local/share/deck-fusion/bin/launch')
    assert "'/home/a b/" in compose_launch('',p,'5')

@pytest.mark.parametrize('before,added,expected',[
    ('',{'dxgi':'n,b'},'dxgi=n,b'),('version=n,b',{'dxgi':'n,b'},'version=n,b;dxgi=n,b'),
    ('dxgi,winmm=n;foo=b',{'dxgi':'n,b'},'winmm=n;foo=b;dxgi=n,b'),
    ('DXGI.DLL=n;dinput8=n,b',{'dxgi':'n,b'},'dinput8=n,b;dxgi=n,b')])
def test_dll_merge(before,added,expected): assert merge_dll_overrides(before,added)==expected


def test_runtime_environment():
    env=launch_environment({'api':'dx12','base_fps':30,'lsfg':{'enabled':True},'lsfg_config':'/x/config.toml','dll_overrides':{'winmm':'n,b'},'enable_nvapi':True},
        {'PATH':'/bin','CUSTOM':'keep','LSFGVK_ENV':'1','LSFGVK_PROFILE':'wrong','WINEDLLOVERRIDES':'dinput8=n,b'})
    assert env['CUSTOM']=='keep' and env['DXVK_FRAME_RATE']=='30' and env['VKD3D_FRAME_RATE']=='30'
    assert env['DECK_FUSION_LSFG']=='1' and env['LSFGVK_CONFIG']=='/x/config.toml'
    assert 'LSFGVK_ENV' not in env and 'LSFGVK_PROFILE' not in env
    assert env['WINEDLLOVERRIDES']=='dinput8=n,b;winmm=n,b'


def test_native_cap_not_claimed():
    env=launch_environment({'api':'vulkan','base_fps':30},{})
    assert 'DXVK_FRAME_RATE' not in env and 'VKD3D_FRAME_RATE' not in env


def test_fail_open_runtime_and_spaces(installation,tmp_path):
    engine,p,root,exe=installation
    stub=tmp_path/'game with spaces.py';output=tmp_path/'result.json'
    stub.write_text('import json,os,sys\nopen(sys.argv[1],"w").write(json.dumps({"args":sys.argv[2:],"test":os.environ.get("DXVK_FRAME_RATE")}))\n')
    import sys
    process=subprocess.run([str(engine.wrapper),'123','--',sys.executable,str(stub),str(output),'one two','ümlaut'],capture_output=True,text=True)
    assert process.returncode==0 and 'launching without added environment' in process.stderr
    assert json.loads(output.read_text())['args']==['one two','ümlaut']


def test_wrapper_uses_stored_config(installation,tmp_path):
    engine,p,root,exe=installation
    store=engine.store('123');store.mkdir(parents=True)
    (store/'runtime.json').write_text(json.dumps({'api':'dx11','base_fps':37}))
    import sys
    result=subprocess.run([str(engine.wrapper),'123','--',sys.executable,'-c','import os;print(os.environ["DXVK_FRAME_RATE"])'],capture_output=True,text=True)
    assert result.returncode==0 and result.stdout.strip()=='37'
    assert (store/'last-launch.json').is_file()
