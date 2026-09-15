"""FSR4xyz integration. Synthetic GPUs and PE files; no rendering claims."""
import copy
import json
import zipfile
from pathlib import Path
import pytest
from conftest import pe_bytes
from fusion_catalog import FSR4FIX
from fusion_downloads import Packages
from fusion_policy import hardware_info
from fusion_util import FusionError, atomic_json, sha256
from test_110 import fsr_payload
from test_120 import apply


def gpu(sysfs,number,device,vendor='0x1002'):
    base=sysfs/f'class/drm/card{number}/device';base.mkdir(parents=True)
    (base/'vendor').write_text(vendor);(base/'device').write_text(device)


@pytest.mark.parametrize('model',['Jupiter','Galileo','Steam Deck'])
def test_deck_dmi_defaults_on_without_drm(tmp_path,model):
    dmi=tmp_path/'devices/virtual/dmi/id';dmi.mkdir(parents=True);(dmi/'product_name').write_text(model)
    h=hardware_info(tmp_path)
    assert h['steam_deck'] and h['fsr4_rdna2_recommended']


@pytest.mark.parametrize('device',['0x163f','0x1435','0x73bf','0x73df','0x73ff','0x743f','0x1681','0x164e'])
def test_rdna2_pci_defaults_on(tmp_path,device):
    gpu(tmp_path,0,device)
    assert hardware_info(tmp_path)['fsr4_rdna2_recommended']


@pytest.mark.parametrize('device,vendor',[('0x744c','0x1002'),('0x73bf','0x10de'),('0xffff','0x1002'),('0x1234','0x8086')])
def test_rdna3_nvidia_intel_unknown_default_off(tmp_path,device,vendor):
    gpu(tmp_path,0,device,vendor)
    assert not hardware_info(tmp_path)['fsr4_rdna2_recommended']


def test_mixed_gpus_do_not_guess_renderer(tmp_path):
    gpu(tmp_path,0,'0x163f');gpu(tmp_path,1,'0x744c')
    dmi=tmp_path/'devices/virtual/dmi/id';dmi.mkdir(parents=True);(dmi/'product_name').write_text('Jupiter')
    h=hardware_info(tmp_path);assert h['has_rdna2'] and not h['fsr4_rdna2_recommended']
    assert not hardware_info(tmp_path/'missing')['fsr4_rdna2_recommended']


def test_hardware_default_only_for_unset_choice(installation,monkeypatch):
    e,p,_,_=installation
    monkeypatch.setattr(e,'hardware',lambda:{'fsr4_rdna2_recommended':True})
    assert e.profile('123')['opti']['fsr4_rdna2_fix'] is True
    p['opti']['fsr4_rdna2_fix']=False;atomic_json(e.store('123')/'profile.json',p)
    assert e.profile('123')['opti']['fsr4_rdna2_fix'] is False
    p['opti']['fsr4_rdna2_fix']=True;atomic_json(e.store('123')/'profile.json',p)
    monkeypatch.setattr(e,'hardware',lambda:{'fsr4_rdna2_recommended':False})
    assert e.profile('123')['opti']['fsr4_rdna2_fix'] is True


def fix_package(e,tmp_path,monkeypatch,kind=64):
    archive=tmp_path/'fix.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('4.1.1b/amd_fidelityfx_upscaler_dx12.dll',pe_bytes(bits=kind)+b'SYNTHETIC-RDNA2-FIX')
    # Unit fixture substitutes the pinned archive hash explicitly, never bypasses production checks.
    monkeypatch.setitem(FSR4FIX,'sha256',sha256(archive))
    meta={'sha256':sha256(archive),'source':'unit-test'}
    return e.packages.install_archive('fsr4fix',FSR4FIX['version'],archive,meta,lambda *_:None),archive,meta


def test_fix_requires_enabled_opti_and_fsr4(packages):
    e,p,_,_=packages;p['opti']['fsr4_rdna2_fix']=True
    assert not any(x['id']=='fsr4fix' for x in e.requirements(p)['items'])
    p['opti'].update(enabled=True,fsr_mode='fsr3')
    assert not any(x['id']=='fsr4fix' for x in e.requirements(p)['items'])
    p['opti']['fsr_mode']='fsr4_int8'
    item=next(x for x in e.requirements(p)['items'] if x['id']=='fsr4fix')
    assert not item['ready'] and item['version']=='4.1.1b'
    p['opti']['fsr4_rdna2_fix']=False
    assert not any(x['id']=='fsr4fix' for x in e.requirements(p)['items'])


def test_selected_fix_deploys_and_uncheck_reverts_standard(packages,tmp_path,monkeypatch):
    e,p,root,exe=packages;base=fsr_payload(e)
    stock=(base/'amd_fidelityfx_upscaler_dx12.dll').read_bytes()
    pkg,_,_=fix_package(e,tmp_path,monkeypatch)
    assert e.fsr4fix_binary().read_bytes().endswith(b'SYNTHETIC-RDNA2-FIX')
    p['api']='dx12';p['opti'].update(enabled=True,fsr_mode='fsr4_int8',fsr4_rdna2_fix=True)
    assert next(x for x in e.requirements(p)['items'] if x['id']=='fsr4fix')['ready']
    plan,prepared=apply(e,p)
    target=exe.parent/'amd_fidelityfx_upscaler_dx12.dll'
    assert target.read_bytes()==e.fsr4fix_binary().read_bytes()
    assert any('the3rdparty1917/fsr4xyz' in warning for warning in plan['warnings'])
    assert (base/'amd_fidelityfx_upscaler_dx12.dll').read_bytes()==stock
    p['opti']['fsr4_rdna2_fix']=False
    apply(e,p,prepared['launch_after'])
    assert target.read_bytes()==stock


def test_cached_fix_tamper_blocks_then_repair_replaces_generation(packages,tmp_path,monkeypatch):
    e,p,_,_=packages;pkg,archive,meta=fix_package(e,tmp_path,monkeypatch)
    e.fsr4fix_binary().write_bytes(b'corrupted')
    with pytest.raises(FusionError,match='changed or is missing'):e.fsr4fix_binary()
    p['opti'].update(enabled=True,fsr_mode='fsr4_int8',fsr4_rdna2_fix=True)
    assert not next(x for x in e.requirements(p)['items'] if x['id']=='fsr4fix')['ready']
    repaired=e.packages.install_archive('fsr4fix',FSR4FIX['version'],archive,meta,lambda *_:None)
    assert repaired['path']!=pkg['path'] and e.fsr4fix_binary().read_bytes().startswith(b'MZ')


def test_wrong_hash_and_32_bit_archive_rejected(packages,tmp_path,monkeypatch):
    e,_,_,_=packages
    archive=tmp_path/'bad.zip';archive.write_bytes(b'bad')
    with pytest.raises(FusionError,match='pinned'):e.packages.install_archive('fsr4fix','4.1.1b',archive,{'sha256':sha256(archive)},lambda *_:None)
    with pytest.raises(FusionError,match='64-bit Windows DLL'):fix_package(e,tmp_path,monkeypatch,kind=32)


def test_resolver_pins_source_version_and_digest(packages):
    e,_,_,_=packages
    a=e.packages.resolve('fsr4fix',lambda *_:None,latest=True)
    assert a['version']=='4.1.1b' and a['expected']==FSR4FIX['sha256'] and a['url']==FSR4FIX['url']
