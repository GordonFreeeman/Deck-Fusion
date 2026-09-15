"""Regression fixtures, not copies of Cyberpunk or any third-party tool binary."""
from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
import struct
import pytest
from conftest import pe_bytes, ROOT
from fusion_engine import Engine
from fusion_steam import installed_games, pe_info, scan_game
from fusion_util import FusionError, atomic_json


def write_large_pe(path: Path, broken_import=False):
    """Sparse image with real PE structures and imports six MiB into the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header=bytearray(pe_bytes(64,'dx12'))
    section=0x80+24+240
    struct.pack_into('<I',header,section+20,6*1024*1024)
    if broken_import: struct.pack_into('<I',header,0x400+12,0x7fffffff)
    with path.open('wb') as f:
        f.write(header[:0x400]);f.seek(6*1024*1024);f.write(header[0x400:])


def shortcuts(home, count=1000):
    steam=home/'.local/share/Steam'
    emulator=home/'Applications/VICE';emulator.parent.mkdir(exist_ok=True);emulator.write_bytes(b'\x7fELF\x02'+b'\0'*128)
    def obj(key):return b'\0'+key.encode()+b'\0'
    def text(key,value):return b'\1'+key.encode()+b'\0'+value.encode()+b'\0'
    data=obj('shortcuts')
    for i in range(count):
        data+=obj(str(i))+b'\2appid\0'+struct.pack('<I',0x80000000+i)+text('AppName',f'C64 fixture {i:04d}')+text('Exe',f'"{emulator}"')+b'\x08'
    data+=b'\x08\x08'
    file=steam/'userdata/123/config/shortcuts.vdf';file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
    return file


def test_large_pe_import_is_detected(tmp_path):
    exe=tmp_path/'bin/x64/Cyberpunk2077.exe';write_large_pe(exe)
    info=pe_info(exe)
    assert info['bits']==64 and info['kind']=='pe' and info['api']=='dx12'
    assert 'd3d12.dll' in info['imports']


def test_bad_optional_import_preserves_executable(tmp_path):
    exe=tmp_path/'Game.exe';write_large_pe(exe,True)
    info=pe_info(exe)
    assert info['kind']=='pe' and info['bits']==64 and info['imports_incomplete']
    assert info['api']=='auto'


def test_real_exe_ranked_ahead_of_reporters_and_launcher(tmp_path):
    exe=tmp_path/'bin/x64/Cyberpunk2077.exe';write_large_pe(exe)
    for name in ['REDEngineErrorReporter.exe','REDprelauncher.exe']:(tmp_path/name).write_bytes(pe_bytes())
    found=scan_game(tmp_path)['candidates']
    assert found[0]['path']==str(exe)
    assert len(found)==3
    assert found[-1]['support']


def test_unreal_engine_subtree_and_legitimate_crash_game_not_omitted(tmp_path):
    exe=tmp_path/'Engine/Binaries/Win64/CrashBandicoot.exe';exe.parent.mkdir(parents=True);exe.write_bytes(pe_bytes())
    result=scan_game(tmp_path)
    assert result['candidates'][0]['path']==str(exe)
    assert not result['candidates'][0]['support']


def test_default_library_skips_thousand_shortcuts(installation,monkeypatch):
    e,*_=installation;file=shortcuts(e.home)
    read_bytes=Path.read_bytes
    def guard(path):
        assert path!=file,'Default filtering must avoid even parsing large EmuDeck shortcut files'
        return read_bytes(path)
    monkeypatch.setattr(Path,'read_bytes',guard)
    assert [g['appid'] for g in e.games()]==['123']


def test_shortcut_toggle_persists_without_removing_profiles(installation):
    e,*_=installation;shortcuts(e.home)
    assert not e.settings()['include_shortcuts']
    e.set_settings({'include_shortcuts':True})
    assert len(e.games())==1001
    restarted=Engine(e.home,ROOT)
    assert restarted.settings()['include_shortcuts']
    profile=restarted.profile(str(0x80000000))
    assert profile['name']=='C64 fixture 0000'
    atomic_json(restarted.store(profile['appid'])/'profile.json',profile)
    restarted.set_settings({'include_shortcuts':False})
    assert len(restarted.games())==1
    assert restarted.profile(profile['appid'])['name']=='C64 fixture 0000'
    assert (restarted.store(profile['appid'])/'profile.json').exists()


@pytest.mark.parametrize('value',[1,0,'true',None,[],{}])
def test_library_toggle_requires_boolean(installation,value):
    with pytest.raises(FusionError):installation[0].set_settings({'include_shortcuts':value})


def test_lossless_software_hidden_but_dll_discovery_still_works(installation):
    e,*_=installation;apps=e.home/'.local/share/Steam/steamapps'
    root=apps/'common/Lossless Scaling';root.mkdir()
    dll=root/'lsfg-vk.dll';dll.write_bytes(pe_bytes())
    (apps/'appmanifest_993090.acf').write_text('"AppState" { "appid" "993090" "name" "Lossless Scaling" "installdir" "Lossless Scaling" }')
    assert '993090' not in [g['appid'] for g in e.games()]
    assert e.lsfg_dll()==dll


def test_review_missing_component_has_actionable_message(installation):
    e,p,*_=installation;p['opti']['enabled']=True
    with pytest.raises(FusionError,match='Tools'):e.review(p,'--skip-launcher')


@pytest.mark.parametrize('mode',['off','standalone','opti'])
def test_review_uses_valid_configuration_without_modifying_game(packages,mode):
    e,p,root,exe=packages;p['reshade']['mode']=mode;p['opti']['enabled']=mode=='opti';p['lsfg']['enabled']=True
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    result=e.review(p,'--skip-launcher')
    assert '%command%' in result['launch_after'] and '--skip-launcher' in result['launch_after']
    assert result['effective_runtime']['lsfg']['enabled']
    assert before=={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    assert not (e.store(p['appid'])/'pending.json').exists()
    assert result['file_count']>0 if mode!='off' else result['file_count']==0


def test_opti_reshade_review_prepare_finish_restore(packages):
    e,p,root,exe=packages;p['opti']['enabled']=True;p['reshade']['mode']='opti';p['base_fps']=30
    p['reshade']['techniques']=['Curves@Curves.fx']
    p['reshade']['uniforms']={'Curves.fx':{'Contrast':'0.75'}}
    p['opti']['overrides']={'Sharpening':{'Sharpness':'0.7'}}
    prepared=e.prepare(p,'--skip-launcher')
    assert (exe.parent/'ReShade64.dll').is_file()
    assert 'LoadReshade=true' in (exe.parent/'OptiScaler.ini').read_text()
    assert 'Sharpness=0.7' in (exe.parent/'OptiScaler.ini').read_text()
    assert 'Contrast=0.75' in (exe.parent/'DeckFusionPreset.ini').read_text()
    assert not (exe.parent/'runme.bat').exists()
    e.finish(p['appid'],prepared['token'],prepared['launch_after'])
    restore=e.prepare(p,prepared['launch_after'],remove=True)
    assert restore['launch_after']=='--skip-launcher'
    e.finish(p['appid'],restore['token'],restore['launch_after'])
    assert not (exe.parent/'ReShade64.dll').exists()
    assert exe.is_file()


def make_plugin(engine):
    from main import Plugin
    import threading
    plugin=Plugin();plugin._engine=engine;plugin._mutex=threading.RLock();plugin._jobs={};plugin._tasks=set();plugin._closing=False
    return plugin


def test_rpc_expected_error_envelope_and_diagnostic_id(installation):
    e,p,*_=installation;plugin=make_plugin(e)
    result=asyncio.run(plugin.rpc('review',{'profile':p,'launch':None}))
    assert not result['ok']
    assert result['error']['code']=='configuration'
    assert 'launch options' in result['error']['message']
    assert len(result['error']['id'])==10
    assert json.loads((e.data/'last-error.json').read_text())['id']==result['error']['id']


def test_rpc_unexpected_exception_is_visible_not_generic(installation,monkeypatch):
    e,*_=installation;plugin=make_plugin(e)
    def failure():raise ValueError('diagnostic test failure')
    monkeypatch.setattr(e,'games',failure)
    result=asyncio.run(plugin.rpc('state',{}))
    assert not result['ok'] and result['error']['code']=='backend'
    assert result['error']['message']=='ValueError: diagnostic test failure'


def test_review_through_real_async_job(packages):
    e,p,*_=packages;plugin=make_plugin(e);p['opti']['enabled']=True
    async def run():
        start=await plugin.start_job('review',{'profile':p,'launch':'--skip-launcher'})
        assert start['ok'];id=start['result']['id']
        for _ in range(100):
            response=await plugin.get_job(id);assert response['ok']
            if response['result']['state']!='running':return response['result']
            await asyncio.sleep(.01)
        raise AssertionError('Review job did not finish')
    result=asyncio.run(run())
    assert result['state']=='done',result
    assert result['result']['file_count']>=3


def test_schema_returns_real_fixture_fields_and_shader_controls(packages):
    e,p,*_=packages;s=e.schema(p['appid'])
    assert any(f['section']=='Sharpening' and f['key']=='Sharpness' for f in s['opti'])
    curves=next(f for f in s['shaders'] if f['file']=='Curves.fx')
    assert curves['techniques']==['Curves']
    assert curves['uniforms'][0]['name']=='Contrast'
