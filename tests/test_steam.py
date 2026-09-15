import struct
from pathlib import Path
import pytest
from conftest import pe_bytes
from fusion_steam import *
from fusion_util import FusionError

@pytest.mark.parametrize('bits,api',[(64,'dx11'),(64,'dx12'),(32,'dx9'),(32,'opengl'),(64,'vulkan'),(64,'dx10')])
def test_executable_import_detection(tmp_path,bits,api):
    file=tmp_path/'test.exe';file.write_bytes(pe_bytes(bits,api))
    info=pe_info(file)
    assert info['kind']=='pe' and info['bits']==bits and info['api']==api


def test_native_not_assumed_vulkan(tmp_path):
    p=tmp_path/'native';p.write_bytes(b'\x7fELF\x02'+b'\0'*100)
    assert pe_info(p)['api']=='auto'


def test_vdf_quotes_backslashes_and_comments():
    d=parse_vdf('"root" { // hi\n "path" "C:\\\\Games" "name" "A \\"quoted\\" game" }')
    assert d['root']['name']=='A "quoted" game'


def test_scan_real_shipping_executable(installation):
    e,p,root,exe=installation
    (root/'Launcher.exe').write_bytes(pe_bytes())
    result=scan_game(root)
    assert result['candidates'][0]['path']==str(exe)
    assert e.games()[0]['appid']=='123'


def test_anticheat_marker(installation):
    e,p,root,exe=installation
    (root/'EasyAntiCheat').mkdir()
    assert scan_game(root)['anticheat']==['EasyAntiCheat']


def test_second_library_with_spaces(installation,tmp_path):
    e,p,root,exe=installation
    steam=e.home/'.local/share/Steam';other=tmp_path/'SD library'
    (other/'steamapps/common/Other Game').mkdir(parents=True)
    (other/'steamapps/appmanifest_456.acf').write_text('"AppState" {"appid" "456" "name" "Other" "installdir" "Other Game"}')
    (steam/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "0" {"path" "'+str(steam)+'"} "1" {"path" "'+str(other)+'"} }')
    assert {x['appid'] for x in e.games()}=={'123','456'}


def test_binary_shortcut_vdf():
    data=b'\0shortcuts\0\0000\0\x02appid\0'+struct.pack('<I',0xf1234567)+b'\x01AppName\0Example\0\x08\x08\x08'
    parsed=binary_vdf(data)
    assert parsed['shortcuts']['0']['appid']==0xf1234567


def makeproc(root,pid,args,env=()):
    p=root/str(pid);p.mkdir();(p/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0');(p/'environ').write_bytes(b'\0'.join(x.encode() for x in env))
    return p


def test_wineserver_and_steam_not_game(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();exe=tmp_path/'game.exe'
    makeproc(proc,101,['wineserver'],['SteamAppId=123'])
    makeproc(proc,102,['steam',str(exe)],['SteamAppId=123'])
    makeproc(proc,103,['other.exe'],['SteamAppId=123'])
    assert not running_game(exe,'123',proc)['running']


def test_actual_game_evidence(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();exe=tmp_path/'game.exe'
    makeproc(proc,105,['wine64',str(exe)],['SteamAppId=123'])
    result=running_game(exe,'123',proc)
    assert result['running'] and result['processes'][0]['pid']==105


def test_same_basename_wrong_app_id_not_game(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();exe=tmp_path/'game.exe'
    makeproc(proc,105,['game.exe'],['SteamAppId=999'])
    assert not running_game(exe,'123',proc)['running']


def test_windows_path_and_matching_id(tmp_path):
    proc=tmp_path/'proc';proc.mkdir();exe=tmp_path/'game.exe'
    makeproc(proc,105,['wine64',r'C:\\installed\\GAME.EXE'],['SteamAppId=123'])
    assert running_game(exe,'123',proc)['running']
