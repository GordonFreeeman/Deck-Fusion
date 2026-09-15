"""ReShade source discovery and preset editing; no source code is executed."""
from __future__ import annotations
import re
from pathlib import Path
from fusion_util import FusionError, ini_read, ini_set, ini_write

SAFE_EXT = {'.fx', '.fxh', '.png', '.dds', '.jpg', '.jpeg', '.bmp', '.tga', '.lut', '.cube', '.txt', '.md', '.license'}
UNIFORM = re.compile(r'\buniform\s+(bool|int|uint|float)([234]?)\s+(\w+)\s*(?:<([\s\S]*?)>)?\s*(?:=\s*([^;]+))?;', re.M)
TECHNIQUE = re.compile(r'^\s*technique(?:10|11|12)?\s+(\w+)\b', re.M)
ANNOTATION = re.compile(r'\b(\w+)\s*=\s*("(?:\\.|[^"\\])*"|[^;]+);')


def unquote(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\0', '\0')
    return value.strip()


def parse_shader(text: str, filename: str) -> dict:
    text = re.sub(r'/\*[\s\S]*?\*/', '', text)
    text = re.sub(r'//[^\n]*', '', text)
    uniforms = []
    for m in UNIFORM.finditer(text):
        base, vector, name, attrs, default = m.groups()
        annotations = {k: unquote(v) for k, v in ANNOTATION.findall(attrs or '')}
        if 'source' in annotations: continue  # Runtime uniforms are not user controls.
        value = (default or ('false' if base == 'bool' else '0')).strip()
        value = re.sub(r'^(?:float|int|uint)[234]\((.*)\)$', r'\1', value)
        value = value.strip('{} ')
        uniforms.append({'name': name, 'type': base + vector, 'default': value,
                         'label': annotations.get('ui_label', name), 'help': annotations.get('ui_tooltip', ''),
                         'ui': annotations.get('ui_type', ''), 'min': annotations.get('ui_min'),
                         'max': annotations.get('ui_max'), 'step': annotations.get('ui_step'),
                         'items': annotations.get('ui_items', '').split('\0')})
    return {'file': filename, 'techniques': list(dict.fromkeys(TECHNIQUE.findall(text))), 'uniforms': uniforms}


def pack_files(info: dict) -> tuple[dict[str, Path], list[dict]]:
    root = Path(info['path'])
    result, schema = {}, []
    for file in sorted(root.rglob('*')):
        if not file.is_file() or file.is_symlink() or file.suffix.lower() not in SAFE_EXT: continue
        if file.stat().st_size > 128 * 1024 * 1024: raise FusionError(f'Shader asset is too large: {file.name}')
        rel = file.relative_to(root).as_posix()
        result[rel] = file
        if file.suffix.lower() == '.fx' and file.stat().st_size < 2 * 1024 * 1024:
            parsed = parse_shader(file.read_text('utf-8', errors='replace'), file.name)
            parsed['relative'] = rel; schema.append(parsed)
    return result, schema


def preset_text(settings: dict) -> str:
    raw = settings.get('raw_preset', '')
    if len(raw) > 1024 * 1024: raise FusionError('Preset exceeds 1 MB.')
    config = ini_read(raw)
    selected = settings.get('techniques', [])
    if not isinstance(selected, list) or len(selected) > 2048:
        raise FusionError('Invalid shader selection.')
    for key in selected:
        if not re.fullmatch(r'[\w]+@[\w .+()\-]+\.fx', key):
            raise FusionError(f'Invalid ReShade technique identifier: {key}')
    ini_set(config, '__ROOT__', 'Techniques', ','.join(selected))
    ini_set(config, '__ROOT__', 'TechniqueSorting', ','.join(selected))
    for filename, values in settings.get('uniforms', {}).items():
        if not re.fullmatch(r'[\w .+()\-]+\.fx', filename): raise FusionError('Invalid shader parameter section.')
        for name, value in values.items():
            if not re.fullmatch(r'\w+', name) or any(c in str(value) for c in '\n\r\0'):
                raise FusionError('Invalid shader parameter value.')
            ini_set(config, filename, name, str(value))
    return ini_write(config)


def opti_schema(text: str) -> list[dict]:
    section, comments, result = '', [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(';'):
            content = line.lstrip('; ').strip()
            if content and set(content) != {'-'}: comments.append(content)
        elif line.startswith('[') and line.endswith(']'):
            section = line[1:-1]; comments = []
        elif '=' in line and not line.startswith('#'):
            name, value = line.split('=', 1)
            if section:
                result.append({'section': section, 'key': name.strip(), 'value': value.strip(),
                               'help': '\n'.join(comments[-10:])})
            comments = []
        elif not line: comments = []
    return result
