"""Regression coverage for registry inspection and removal discovery."""
from pathlib import Path
import pytest
from fusion_removal import GraphicsRemoval
from fusion_wine import registry_entries
from fusion_util import FusionError
from test_removal import ctx, commit


@pytest.mark.parametrize('value,order',[
    ('native,builtin','n,b'),('builtin,native','b,n'),('n b','n,b'),
    ('native','n'),('builtin','b'),('',''),('disabled',''),
    ('Native, Builtin, native','n,b'),('native;builtin','n'),
])
def test_registry_load_orders_and_later_entries_are_read_without_rewriting(tmp_path,value,order):
    text='WINE REGISTRY Version 2\n[Software\\\\Wine\\\\DllOverrides]\n"example"="'+value+'"\n"winmm"="native,builtin"\n'
    reg=tmp_path/'user.reg';reg.write_text(text)
    entries,warnings=registry_entries(tmp_path,'game.exe')
    assert not warnings
    assert {x['name']:x['order'] for x in entries}=={'example':order,'winmm':'n,b'}
    assert entries[0]['raw_order']==value and reg.read_text()==text


def add_injector(e,exe):
    dll=exe.parent/'winmm.dll'
    dll.write_bytes((Path(e.packages.status()['opti']['path'])/'OptiScaler.dll').read_bytes())
    return dll


def prefix_for(e,p):
    prefix=Path(e.game(p['appid'])['library'])/'steamapps/compatdata'/p['appid']/'pfx'
    prefix.mkdir(parents=True,exist_ok=True)
    return prefix


def test_disabled_unrelated_override_no_longer_blocks_removal_and_prefix_is_unchanged(packages):
    e,p,root,exe,m,payload=ctx(packages);dll=add_injector(e,exe)
    prefix=prefix_for(e,p)
    text='WINE REGISTRY Version 2\n[Software\\\\Wine\\\\DllOverrides]\n"unrelated"="disabled"\n"ucrtbase"="native"\n"winmm"="native,builtin"\n'
    (prefix/'user.reg').write_text(text)
    assert m.status(payload)['has_installation']
    assert m.plan(payload)['file_count']==1
    commit(e,m,payload)
    assert not dll.exists() and (prefix/'user.reg').read_text()==text
    status=m.status(payload)
    assert not status['has_installation'] and status['undo_available']


@pytest.mark.parametrize('name',['winmm','*winmm','C:\\\\mods\\\\winmm.dll'])
def test_relevant_native_only_registry_override_still_protects_the_game(packages,name):
    e,p,root,exe,m,payload=ctx(packages);dll=add_injector(e,exe)
    prefix=prefix_for(e,p)
    (prefix/'user.reg').write_text('WINE REGISTRY Version 2\n[Software\\\\Wine\\\\DllOverrides]\n"unrelated"="disabled"\n"'+name+'"="native"\n')
    assert m.status(payload)['has_installation']
    with pytest.raises(FusionError,match='native-only'):m.plan(payload)
    assert dll.exists()


def test_unreadable_registry_remains_a_removal_blocker_with_a_single_message(packages):
    e,p,root,exe,m,payload=ctx(packages);dll=add_injector(e,exe)
    prefix=prefix_for(e,p);(prefix/'user.reg').write_bytes(b'WINE REGISTRY Version 2\n\xff')
    assert m.status(payload)['has_installation']
    with pytest.raises(FusionError,match='Cannot verify prefix') as error:m.plan(payload)
    assert str(error.value).count('Cannot completely inspect user.reg')==1 and dll.exists()


def test_unknown_proxy_names_and_presets_do_not_offer_removal(packages):
    e,p,root,exe,m,payload=ctx(packages)
    (exe.parent/'version.dll').write_bytes(b'game-owned DLL')
    (exe.parent/'ReShade.ini').write_text('untracked preset')
    assert not m.status(payload)['has_installation']
    dll=add_injector(e,exe);assert m.status(payload)['has_installation']
    dll.unlink();assert not m.status(payload)['has_installation']
    assert (exe.parent/'version.dll').read_bytes()==b'game-owned DLL'


def test_ambiguous_or_linked_injectors_are_not_offered_as_safe_removal(packages,tmp_path):
    e,p,root,exe,m,payload=ctx(packages);dll=add_injector(e,exe)
    (exe.parent/'WINMM.dll').write_bytes(dll.read_bytes())
    assert not m.status(payload)['has_installation']
    dll.unlink();(exe.parent/'WINMM.dll').unlink()
    external=tmp_path/'outside.dll';external.write_bytes((Path(e.packages.status()['opti']['path'])/'OptiScaler.dll').read_bytes())
    dll.symlink_to(external);assert not m.status(payload)['has_installation'] and external.exists()
