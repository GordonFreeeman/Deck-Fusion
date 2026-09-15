"""Small, dependency-free safety primitives. No subprocess shell execution."""
from __future__ import annotations
import configparser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any

class FusionError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_bytes(path: Path, value: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise FusionError(f'Refusing to replace a symlink: {path}')
    fd, tmp = tempfile.mkstemp(prefix='.fusion-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        try:
            dfd = os.open(path.parent, os.O_DIRECTORY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def atomic_json(path: Path, data: Any) -> None:
    atomic_bytes(path, (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode())


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists(): return default
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, ValueError) as e:
        raise FusionError(f'Cannot read {path.name}: {e}. The original file has not been overwritten.') from e


def safe_relative(name: str) -> str:
    if '\\' in name: name = name.replace('\\', '/')
    p = PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(s in ('..', '') for s in p.parts) or ':' in name or '\x00' in name:
        raise FusionError(f'Unsafe archive/file path: {name!r}')
    return str(p)


def safe_target(root: Path, relative: str) -> Path:
    p = root / safe_relative(relative)
    root_real = root.resolve()
    if not p.resolve().is_relative_to(root_real):
        raise FusionError(f'Path leaves the selected directory: {relative}')
    cur = p
    while cur != root:
        if cur.is_symlink():
            raise FusionError(f'Symbolic links are not modified: {cur}')
        cur = cur.parent
    return p


def ini_read(text: str) -> configparser.ConfigParser:
    p = configparser.ConfigParser(interpolation=None, strict=False, delimiters=('=',), comment_prefixes=(';', '#'))
    p.optionxform = str
    # ReShade presets have a legal nameless/global section before the first [section].
    p.read_string('[__ROOT__]\n' + text.lstrip('\ufeff'))
    return p


def ini_write(p: configparser.ConfigParser) -> str:
    import io
    s = io.StringIO()
    p.write(s, space_around_delimiters=False)
    return s.getvalue().replace('[__ROOT__]\n', '', 1).lstrip('\n')


def ini_set(p: configparser.ConfigParser, section: str, key: str, value: Any) -> None:
    if not p.has_section(section): p.add_section(section)
    p.set(section, key, str(value))


def ini_patch(text: str, changes: dict[str, dict[str, str]]) -> str:
    """Patch values without discarding upstream comments, unknown options, or casing."""
    import re
    # SimpleIni (used by OptiScaler) is case-insensitive. Patch every occurrence,
    # including repeated sections/keys, so a stale later true cannot shadow false.
    wanted = {(section.casefold(), key.casefold()): str(value)
              for section, values in changes.items() for key, value in values.items()}
    remaining = {(section.casefold(), key.casefold()): (section, key, str(value))
                 for section, values in changes.items() for key, value in values.items()}
    output: list[str] = []
    section = '__ROOT__'
    def flush(sec: str) -> None:
        for pair, (_, key, value) in list(remaining.items()):
            if pair[0] == sec.casefold():
                output.append(f'{key}={value}')
                del remaining[pair]
    for line in text.lstrip('\ufeff').splitlines():
        m = re.match(r'^\s*\[([^\]]+)\]', line)
        if m:
            flush(section)
            section = m.group(1).strip()
        elif '=' in line and not line.lstrip().startswith((';', '#')):
            key = line.split('=', 1)[0].strip()
            pair = (section.casefold(), key.casefold())
            if pair in wanted:
                line = key + '=' + wanted[pair]
                remaining.pop(pair, None)
        output.append(line)
    flush(section)
    for section, values in changes.items():
        missing = [(key, value) for (sec, _), (_, key, value) in remaining.items()
                   if sec == section.casefold()]
        if missing:
            if section != '__ROOT__': output.extend(['', f'[{section}]'])
            output.extend(f'{key}={value}' for key, value in missing)
    return '\n'.join(output) + '\n'
