"""Validate a per-game manual OptiScaler INI and mirror runtime-sensitive values."""
import configparser
import copy
from fusion_util import FusionError


def parse_manual(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>1024*1024 or '\0' in text:
        raise FusionError('OptiScaler INI must be UTF-8 text, at most 1 MB, without null characters.')
    parser=configparser.ConfigParser(interpolation=None,strict=True,delimiters=('=',),comment_prefixes=(';','#'),empty_lines_in_values=False)
    parser.optionxform=str
    try: parser.read_string(text.lstrip('\ufeff'))
    except configparser.Error as error: raise FusionError('Invalid OptiScaler INI: '+str(error)) from error
    sections={};pairs=set()
    for section in parser.sections():
        folded=section.casefold()
        if folded in sections:raise FusionError('Duplicate OptiScaler section: '+section)
        sections[folded]={}
        for key,value in parser.items(section,raw=True):
            pair=(folded,key.casefold())
            if pair in pairs or any(c in value for c in '\r\n'):raise FusionError('Duplicate or multiline OptiScaler value: '+section+'.'+key)
            pairs.add(pair);sections[folded][key.casefold()]=value.strip()
    if parser.defaults():raise FusionError('DEFAULT inheritance is not supported by OptiScaler.')
    for section,key in [('upscalers','dx11upscaler'),('upscalers','dx12upscaler'),('upscalers','vulkanupscaler'),('framegen','enabled')]:
        if key not in sections.get(section,{}):raise FusionError('Keep the required OptiScaler setting '+section+'.'+key+'.')
    return sections


def apply_manual(o):
    text=o.get('manual_ini','')
    if not isinstance(text,str):raise FusionError('Invalid manual OptiScaler configuration.')
    if not text:return o
    sections=parse_manual(text)
    for key,field in [('dx11upscaler','dx11'),('dx12upscaler','dx12'),('vulkanupscaler','vulkan')]:
        o[field]=sections['upscalers'][key].lower()
    enabled=sections['framegen']['enabled'].lower()
    if enabled not in ('true','false'):raise FusionError('Set FrameGen.Enabled to true or false explicitly in manual mode.')
    o['fg']=enabled=='true'
    values={key:value.lower() for section in sections.values() for key,value in section.items()}
    o['fsr4_watermark']=values.get('fsr4enablewatermark')=='true'
    o['mouse_input']={'true':'polling','false':'window'}.get(values.get('manualinputpolling'),'auto')
    o['steam_input']={'false':'keep','true':'disable'}.get(values.get('disableoverlays'),'auto')
    o['fsr_mode']='fsr4_int8' if values.get('fsr4forcemodel')=='2' or values.get('fsr4forceenableint8')=='true' else 'auto'
    # A manual FSR3 routing decision must not make the guided resolver change XeSS.
    return o


def reset_manual(o):
    from fusion_catalog import DEFAULT_PROFILE
    for key in ('dx11','dx12','vulkan','fg','spoof','fsr_mode','fsr4_watermark','mouse_input','steam_input','overrides','manual_ini'):
        o[key]=copy.deepcopy(DEFAULT_PROFILE['opti'][key])
    o['manual_reset']=True
    return o
