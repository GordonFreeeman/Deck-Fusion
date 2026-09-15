import json
import struct
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'py_modules'))
sys.path.insert(0,str(ROOT))
from fusion_engine import Engine
from fusion_util import atomic_json


def pe_bytes(bits=64, api='dx11'):
    data=bytearray(8192); data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,0x80)
    off=0x80;data[off:off+4]=b'PE\0\0'
    struct.pack_into('<HH',data,off+4,0x8664 if bits==64 else 0x14c,1)
    size=240 if bits==64 else 224
    struct.pack_into('<H',data,off+20,size);struct.pack_into('<H',data,off+24,0x20b if bits==64 else 0x10b)
    table=off+24+size
    struct.pack_into('<IIII',data,table+8,2048,0x1000,2048,0x400)
    if api:
        directory=off+24+(112 if bits==64 else 96)
        struct.pack_into('<II',data,directory+8,0x1000,40)
        struct.pack_into('<IIIII',data,0x400,0,0,0,0x1100,0x1200)
        dll={'dx9':'d3d9.dll','dx10':'d3d10.dll','dx11':'d3d11.dll','dx12':'d3d12.dll','vulkan':'vulkan-1.dll','opengl':'opengl32.dll'}[api].encode()+b'\0'
        data[0x500:0x500+len(dll)]=dll
    return bytes(data)


def vc_fixture(prefix, bits=64, version=(14,44,35211,0)):
    """Synthetic version-resource/registry evidence; never a runnable VC DLL."""
    data = bytearray(pe_bytes(bits, api=None))
    key = 'VS_VERSION_INFO\0'.encode('utf-16le')
    data[0x706:0x706+len(key)] = key
    offset = (0x706 + len(key) + 3) & ~3
    struct.pack_into('<4I', data, offset, 0xFEEF04BD, 0x10000,
                     version[0] << 16 | version[1], version[2] << 16 | version[3])
    publisher = 'Microsoft Corporation'.encode('utf-16le')
    data[0x800:0x800+len(publisher)] = publisher
    reg = prefix / 'system.reg'
    is64 = '#arch=win64' in reg.read_text()
    folder = prefix / 'drive_c/windows' / ('system32' if bits==64 or not is64 else 'syswow64')
    folder.mkdir(parents=True, exist_ok=True)
    names = ['vcruntime140.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll']
    if bits == 64: names.append('vcruntime140_1.dll')
    for name in names: (folder / name).write_bytes(data)
    arch = 'x64' if bits == 64 else 'x86'
    with reg.open('a') as f:
        f.write('\n[Software\\\\Microsoft\\\\VisualStudio\\\\14.0\\\\VC\\\\Runtimes\\\\'+arch+']\n"Installed"=dword:00000001\n"Version"="v'+'.'.join(map(str,version))+'"\n')
    return folder


@pytest.fixture
def installation(tmp_path):
    home=tmp_path/'home';home.mkdir()
    steam=home/'.local/share/Steam';apps=steam/'steamapps';apps.mkdir(parents=True)
    root=apps/'common/Test Game';exe=root/'Binaries/Win64/Test-Win64-Shipping.exe';exe.parent.mkdir(parents=True)
    exe.write_bytes(pe_bytes())
    (apps/'libraryfolders.vdf').write_text('"libraryfolders" { "0" { "path" "'+str(steam)+'" } }')
    (apps/'appmanifest_123.acf').write_text('"AppState" { "appid" "123" "name" "Test Game" "installdir" "Test Game" }')
    engine=Engine(home,ROOT)
    p=engine.profile('123');p['exe']=str(exe)
    return engine,p,root,exe


@pytest.fixture
def packages(installation):
    engine,p,root,exe=installation
    base=engine.data/'packages';base.mkdir(exist_ok=True)
    opt=base/'opti-test';opt.mkdir()
    (opt/'OptiScaler.dll').write_bytes(pe_bytes()+b'OptiScaler')
    (opt/'amd_fidelityfx_dx12.dll').write_bytes(pe_bytes()+b'FFX')
    (opt/'runme.bat').write_text('NEVER EXECUTE')
    (opt/'OptiScaler.ini').write_text('''; Official-format fixture, not a real binary payload.
[Upscalers]
; DirectX 11 output
Dx11Upscaler=auto
Dx12Upscaler=auto
VulkanUpscaler=auto
[FrameGen]
Enabled=auto
FGInput=auto
FGOutput=auto
[Plugins]
; Load the ReShade companion
LoadReshade=auto
[Spoofing]
Dxgi=auto
[Sharpening]
; Sharpness from zero to one
Sharpness=auto
''')
    resh=base/'resh-test';resh.mkdir()
    (resh/'ReShade64.dll').write_bytes(pe_bytes()+b'ReShade64')
    (resh/'ReShade32.dll').write_bytes(pe_bytes(32)+b'ReShade32')
    lsfg=base/'lsfg-test';lsfg.mkdir()
    (lsfg/'liblsfg-vk.so').write_bytes(b'\x7fELF\x02'+b'\0'*100)
    (lsfg/'layer.json').write_text(json.dumps({'file_format_version':'1.0.0','layer':{'name':'VK_LAYER_LSFGVK','library_path':'liblsfg-vk.so','type':'GLOBAL','api_version':'1.3.0'}}))
    status={'opti':{'version':'test-0.9.4','path':str(opt),'payload':{'directory':'.','dll':'OptiScaler.dll','ini':'OptiScaler.ini'}},
            'reshade':{'version':'test-6.8.0','path':str(resh),'payload':{'binaries':{'reshade64.dll':'ReShade64.dll','reshade32.dll':'ReShade32.dll'}}},
            'lsfg':{'version':'2.0.0','path':str(lsfg),'payload':{'manifest':'layer.json','library':'liblsfg-vk.so','supports_32bit':False}},'shaders':{}}
    for key in ('standard','sweetfx','fxshaders'):
        pack=base/key; (pack/'Shaders').mkdir(parents=True)
        (pack/'Textures').mkdir()
        if key=='standard':(pack/'Shaders/ReShade.fxh').write_text('// shared header')
        else:
            filename='Curves.fx' if key=='sweetfx' else 'CAS.fx';tech=filename[:-3]
            (pack/f'Shaders/{filename}').write_text(f'''#include "ReShade.fxh"
uniform float Contrast < ui_min = 0.0; ui_max = 1.0; ui_step = 0.01; ui_label = "Contrast"; > = 0.5;
technique {tech} {{ pass {{}} }}
''')
        status['shaders'][key]={'id':key,'name':key,'path':str(pack),'commit':'f'*40}
    atomic_json(engine.data/'packages.json',status)
    loss=root/'lsfg-vk.dll';loss.write_bytes(pe_bytes()+b'user owned LSFG test fixture')
    engine.setup_lsfg(str(loss))
    return engine,p,root,exe
