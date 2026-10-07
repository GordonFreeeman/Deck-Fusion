"""Bounded PE VERSIONINFO reader. No filename or loose binary-string identification."""
import struct
from pathlib import Path


def version_strings(path: Path) -> dict:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 192 * 1024 * 1024:
            return {}
        data = path.read_bytes()
        def u16(pos): return struct.unpack_from('<H', data, pos)[0]
        def u32(pos): return struct.unpack_from('<I', data, pos)[0]
        if data[:2] != b'MZ': return {}
        pe = u32(0x3c)
        if data[pe:pe+4] != b'PE\0\0' or not u16(pe+22) & 0x2000: return {}
        count, size = u16(pe+6), u16(pe+20)
        if not 1 <= count <= 96: return {}
        opt = pe+24; magic = u16(opt)
        if magic not in (0x10b, 0x20b): return {}
        dirs = opt + (112 if magic == 0x20b else 96)
        rva, resource_size = u32(dirs+16), u32(dirs+20)
        if not rva or not 16 <= resource_size <= 4*1024*1024: return {}
        sections = opt+size
        def offset(addr, length=1):
            for i in range(count):
                pos=sections+i*40; start=u32(pos+12); raw_size=u32(pos+16); raw=u32(pos+20)
                if start <= addr and addr-start+length <= raw_size and raw+addr-start+length <= len(data):
                    return raw+addr-start
            raise ValueError('Invalid resource address')
        base=offset(rva,resource_size)
        def entries(relative):
            if relative<0 or relative+16>resource_size: raise ValueError('Invalid directory')
            pos=base+relative; count=u16(pos+12)+u16(pos+14)
            if count>256 or relative+16+count*8>resource_size: raise ValueError('Invalid directory size')
            return [(u32(pos+16+i*8),u32(pos+20+i*8)) for i in range(count)]
        version_dirs=[dest&0x7fffffff for name,dest in entries(0) if name==16 and dest&0x80000000]
        results={}
        for directory in version_dirs:
            for _,dest in entries(directory):
                if not dest&0x80000000: continue
                for _,leaf in entries(dest&0x7fffffff):
                    if leaf&0x80000000 or leaf+16>resource_size: continue
                    addr,n=u32(base+leaf),u32(base+leaf+4)
                    if not 6<=n<=65536: continue
                    start=offset(addr,n); end=start+n
                    def block(pos,limit,depth=0):
                        if depth>5 or pos+6>limit: return pos
                        length,values,kind=struct.unpack_from('<HHH',data,pos)
                        stop=pos+length
                        if length<6 or stop>limit: raise ValueError('Invalid version block')
                        k=pos+6
                        while k+2<=stop and data[k:k+2]!=b'\0\0': k+=2
                        if k+2>stop: raise ValueError('Invalid version key')
                        key=data[pos+6:k].decode('utf-16le'); value=(k+2+3)&~3
                        size=values*(2 if kind==1 else 1)
                        if value+size>stop: raise ValueError('Invalid version value')
                        if key in ('ProductName','OriginalFilename','InternalName','CompanyName','FileDescription') and kind==1:
                            text=data[value:value+size].decode('utf-16le').rstrip('\0').strip()
                            if key in results and results[key]!=text: raise ValueError('Ambiguous identity')
                            results[key]=text
                        child=(value+size+3)&~3
                        while child+6<=stop:
                            next_pos=block(child,stop,depth+1)
                            if next_pos<=child: break
                            child=(next_pos+3)&~3
                        return stop
                    if data[start+6:start+6+32].decode('utf-16le').rstrip('\0')!='VS_VERSION_INFO': continue
                    block(start,end)
        return results
    except (OSError,ValueError,UnicodeError,struct.error,OverflowError):
        return {}


def identify(path, known=None):
    from fusion_util import sha256
    if known:
        label=known.get(sha256(path))
        if label: return label, 'Exact match to the cached injector DLL'
    info=version_strings(path)
    product=info.get('ProductName','').casefold()
    original=info.get('OriginalFilename','').casefold()
    internal=info.get('InternalName','').casefold()
    if product=='reshade' and (original in ('reshade.dll','reshade32.dll','reshade64.dll') or internal=='reshade'):
        return 'ReShade','PE version resource identifies ReShade'
    if product=='optiscaler' and (original=='optiscaler.dll' or internal in ('optiscaler','optiscaler.dll')):
        return 'OptiScaler','PE version resource identifies OptiScaler'
    return None,None
