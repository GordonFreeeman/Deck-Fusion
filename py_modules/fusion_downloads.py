"""Official-origin downloads and bounded extraction. Windows installers are never run."""
from __future__ import annotations
import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import html
import stat
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable
from fusion_catalog import LSFG_INDEX, LSFG_VERSION, OPTI_API, RESH_SITE, SHADER_PACKS, FSR4FIX
from fusion_util import FusionError, atomic_json, read_json, safe_target, sha256
from fusion_network import tls_context, certificate_error

Progress = Callable[[str, float], None]
HOSTS = {'builds.lsfg-vk.dev', 'lsfg-vk.dev', 'reshade.me', 'www.reshade.me', 'static.reshade.me',
         'api.github.com', 'github.com', 'codeload.github.com', 'raw.githubusercontent.com',
         'release-assets.githubusercontent.com', 'objects.githubusercontent.com', 'github-releases.githubusercontent.com'}
MAX_ARCHIVE = 768 * 1024 * 1024
MAX_EXTRACT = 2 * 1024 * 1024 * 1024
MAX_FILES = 60000


def checked_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        raise FusionError(f'Download source is not an approved HTTPS upstream: {p.hostname}')
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, dest: Path, progress: Progress, expected: str | None = None, limit: int = MAX_ARCHIVE) -> dict:
    checked_url(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + '.part')
    context, trust = tls_context()
    opener = urllib.request.build_opener(SafeRedirect(), urllib.request.HTTPSHandler(context=context))
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DeckFusion/1.0.0 (+SteamDeck; upstream-only downloader)',
                                                        'Accept': '*/*'})
            with opener.open(req, timeout=40) as response:
                checked_url(response.geturl())
                total = int(response.headers.get('Content-Length', '0'))
                if total > limit: raise FusionError('Download exceeds the configured size limit.')
                h = hashlib.sha256(); received = 0; last_progress = 0.
                with partial.open('wb') as f:
                    while True:
                        block = response.read(256 * 1024)
                        if not block: break
                        received += len(block)
                        if received > limit: raise FusionError('Download exceeds the configured size limit.')
                        h.update(block); f.write(block)
                        if time.monotonic() - last_progress > 0.2:
                            progress(f'Downloading {dest.name}: {received // 1024 // 1024} MB', min(.85, received / total * .85) if total else .1)
                            last_progress = time.monotonic()
                    f.flush(); os.fsync(f.fileno())
                if total and received != total: raise FusionError('Incomplete download. No installed files have been changed.')
                digest = h.hexdigest()
                if expected:
                    expected = expected.removeprefix('sha256:').lower()
                    if not re.fullmatch('[0-9a-f]{64}', expected) or digest != expected:
                        raise FusionError('Upstream SHA-256 verification failed. The download was rejected.')
                os.replace(partial, dest)
                return {'url': url, 'final_url': response.geturl(), 'sha256': digest, 'size': received,
                        'upstream_digest_verified': bool(expected), 'downloaded_at': int(time.time()),
                        'tls_verified': True}
        except urllib.error.HTTPError as error:
            last_error = error
            host = urllib.parse.urlsplit(url).hostname
            if error.code in (403, 429):
                retry = error.headers.get('Retry-After') if error.headers else None
                detail = f' Retry after {retry} seconds.' if retry and retry.isdigit() else ''
                raise FusionError(f'{host} refused the download (HTTP {error.code}). This can be a rate limit or access restriction.{detail} Cached tools and installed game files were not changed.') from error
            if error.code < 500:
                raise FusionError(f'{host} returned HTTP {error.code} for {url}. The upstream file may have moved. Cached tools and installed game files were not changed.') from error
            if attempt < 2: time.sleep(.5 * (attempt + 1))
        except (urllib.error.URLError, OSError, ValueError) as error:
            last_error = error
            host = urllib.parse.urlsplit(url).hostname
            if certificate_error(error):
                raise FusionError(f'HTTPS certificate validation failed for {host}. Loaded {trust["ca_count"]} trusted CA certificates. Check the Deck date/time and any HTTPS-inspecting network. Certificate and hostname verification remain enabled; cached tools and game files were not changed. Details: {getattr(error, "reason", error)}') from error
            if attempt < 2: time.sleep(.5 * (attempt + 1))
        finally:
            partial.unlink(missing_ok=True)
    reason = getattr(last_error, 'reason', last_error)
    if isinstance(reason, socket.gaierror):
        detail = 'DNS lookup failed. Check the network connection and DNS settings.'
    elif isinstance(reason, (TimeoutError, socket.timeout)):
        detail = 'The connection timed out. Retry on a working connection.'
    else:
        detail = str(reason)
    raise FusionError(f'Download failed for {urllib.parse.urlsplit(url).hostname}: {detail} Cached tools and installed game files were not changed.')


def get_json(url: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'metadata.json'
        download(url, p, lambda *_: None, limit=16 * 1024 * 1024)
        try: return json.loads(p.read_text('utf-8'))
        except ValueError as e: raise FusionError('The upstream metadata response was not valid JSON.') from e


def _materialize_links(dest: Path, links: list[tuple[str, str, bool]]) -> None:
    import posixpath
    for _ in range(len(links) + 1):
        next_links = []
        for name, target, hard in links:
            if target.startswith('/') or '\\' in target or ':' in target:
                raise FusionError('Archive contains an unsafe link.')
            ref = posixpath.normpath(target if hard else posixpath.join(posixpath.dirname(name), target))
            source = safe_target(dest, ref)
            output = safe_target(dest, name)
            if source.is_file() and not source.is_symlink():
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, output)
            else: next_links.append((name, target, hard))
        if not next_links: return
        if len(next_links) == len(links): break
        links = next_links
    raise FusionError('Archive contains an unresolved link. No installation was performed.')


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()): raise FusionError('Extraction target must be empty.')
    seen = set(); total = 0; links = []
    def claim(name: str, size: int) -> Path:
        nonlocal total
        p = safe_target(dest, name)
        rel = str(p.relative_to(dest)).casefold()
        if rel in seen: raise FusionError(f'Duplicate archive entry: {name}')
        seen.add(rel); total += max(0, size)
        if len(seen) > MAX_FILES or total > MAX_EXTRACT or size < 0:
            raise FusionError('Archive expansion exceeds the safety limit.')
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                if entry.is_dir():
                    safe_target(dest, entry.filename).mkdir(parents=True, exist_ok=True); continue
                p = claim(entry.filename, entry.file_size)
                if stat.S_ISLNK(entry.external_attr >> 16):
                    links.append((entry.filename, z.read(entry).decode('utf-8'), False)); continue
                with z.open(entry) as src, p.open('wb') as out: shutil.copyfileobj(src, out, 1024*1024)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, 'r:*') as tar:
            for entry in tar:
                if entry.isdir():
                    if entry.name.strip('./'): safe_target(dest, entry.name).mkdir(parents=True, exist_ok=True)
                    continue
                p = claim(entry.name, entry.size)
                if entry.issym() or entry.islnk():
                    links.append((entry.name, entry.linkname, entry.islnk())); continue
                if not entry.isfile(): raise FusionError('Archive contains a device or unsupported file type.')
                src = tar.extractfile(entry)
                if src is None: raise FusionError('Could not read archive member.')
                with src, p.open('wb') as out: shutil.copyfileobj(src, out, 1024*1024)
    else:
        _extract_libarchive(archive, dest, claim, links)
    _materialize_links(dest, links)


def _extract_libarchive(archive: Path, dest: Path, claim, links: list) -> None:
    libpath = ctypes.util.find_library('archive')
    if not libpath: raise FusionError('SteamOS libarchive is unavailable. Cannot safely unpack the upstream 7z file. No Windows installer or sudo command was run.')
    lib = ctypes.CDLL(libpath)
    signatures = {
        'archive_read_new': (ctypes.c_void_p, []),
        'archive_read_support_filter_all': (ctypes.c_int, [ctypes.c_void_p]),
        'archive_read_support_format_all': (ctypes.c_int, [ctypes.c_void_p]),
        'archive_read_open_filename': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]),
        'archive_read_next_header': (ctypes.c_int, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]),
        'archive_entry_pathname': (ctypes.c_char_p, [ctypes.c_void_p]),
        'archive_entry_size': (ctypes.c_int64, [ctypes.c_void_p]),
        'archive_entry_filetype': (ctypes.c_uint, [ctypes.c_void_p]),
        'archive_entry_symlink': (ctypes.c_char_p, [ctypes.c_void_p]),
        'archive_entry_hardlink': (ctypes.c_char_p, [ctypes.c_void_p]),
        'archive_read_data': (ctypes.c_ssize_t, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]),
        'archive_read_free': (ctypes.c_int, [ctypes.c_void_p]),
        'archive_error_string': (ctypes.c_char_p, [ctypes.c_void_p]),
    }
    for name, (restype, argtypes) in signatures.items():
        func = getattr(lib, name); func.restype = restype; func.argtypes = argtypes
    handle = lib.archive_read_new()
    def error() -> FusionError:
        message = lib.archive_error_string(handle)
        return FusionError('Archive extraction failed: ' + (message.decode('utf-8', 'replace') if message else 'unsupported archive'))
    try:
        lib.archive_read_support_filter_all(handle); lib.archive_read_support_format_all(handle)
        if lib.archive_read_open_filename(handle, os.fsencode(archive), 1024*1024) != 0: raise error()
        ent = ctypes.c_void_p(); buf = ctypes.create_string_buffer(1024*1024)
        while True:
            ret = lib.archive_read_next_header(handle, ctypes.byref(ent))
            if ret == 1: break
            if ret < 0: raise error()
            raw = lib.archive_entry_pathname(ent)
            if not raw: raise FusionError('Archive entry has no name.')
            name = raw.decode('utf-8', 'strict')
            typ = lib.archive_entry_filetype(ent)
            if stat.S_ISDIR(typ):
                safe_target(dest, name).mkdir(parents=True, exist_ok=True); continue
            size = lib.archive_entry_size(ent)
            p = claim(name, size)
            link = lib.archive_entry_symlink(ent) or lib.archive_entry_hardlink(ent)
            if link:
                links.append((name, link.decode('utf-8'), bool(lib.archive_entry_hardlink(ent)))); continue
            if not stat.S_ISREG(typ) and typ != 0: raise FusionError('Archive contains an unsupported file type.')
            written = 0
            with p.open('wb') as out:
                while True:
                    n = lib.archive_read_data(handle, buf, len(buf))
                    if n < 0: raise error()
                    if n == 0: break
                    written += n
                    if written > size or written > MAX_EXTRACT: raise FusionError('Archive entry exceeds its declared size.')
                    out.write(buf.raw[:n])
            if written != size: raise FusionError('Archive member was truncated.')
    finally: lib.archive_read_free(handle)


class Packages:
    def __init__(self, root: Path, bundled: Path | None = None):
        self.root = root
        self.bundled = bundled
        self._seed_attempted = False
        self._bundle_errors = []
        self.cache = root / 'downloads'
        self.packages = root / 'packages'
        self.cache.mkdir(parents=True, exist_ok=True); self.packages.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict:
        return read_json(self.root / 'packages.json', {})

    def _record(self, key: str, info: dict) -> dict:
        d = self.status(); d[key] = info; atomic_json(self.root / 'packages.json', d); return info

    def _resolve_lsfg(self, progress: Progress, latest: bool) -> tuple[str, str, None]:
        # LSFG's build host has used multiple stable archive names over time
        # (bare, -linux and -x86_64). Discover the exact upstream filename
        # rather than guessing one that may 404. Only stable 2.x tar.xz files
        # are accepted, so dev/rc/git snapshots cannot be selected.
        progress('Resolving the official LSFG 2.x release', .01)
        page = self.cache / 'lsfg-releases.html'
        download(LSFG_INDEX, page, lambda *_: None, limit=4*1024*1024)
        text = html.unescape(page.read_text('utf-8', errors='replace'))
        pattern = re.compile(
            r'(?P<path>(?:https://builds\.lsfg-vk\.dev/|/)?[^"\'<>\s]*?'
            r'lsfg-vk-(?P<version>2\.\d+\.\d+)(?P<suffix>-(?:x86_64|amd64|linux))?\.tar\.xz)',
            re.IGNORECASE,
        )
        releases: dict[str, list[tuple[int, str]]] = {}
        preference = {'-x86_64': 0, '-amd64': 1, '-linux': 2, '': 3}
        for match in pattern.finditer(text):
            version = match.group('version')
            suffix = (match.group('suffix') or '').lower()
            raw = match.group('path')
            url = urllib.parse.urljoin(LSFG_INDEX, raw.lstrip('/'))
            try:
                checked_url(url)
            except FusionError:
                continue
            releases.setdefault(version, []).append((preference.get(suffix, 9), url))
        if not releases:
            raise FusionError('No compatible stable LSFG 2.x release was found on the official build index. Git builds and release candidates were not selected.')
        version = max(releases, key=lambda v: tuple(map(int, v.split('.')))) if latest else LSFG_VERSION
        if version not in releases:
            raise FusionError(f'LSFG {version} was not found on the official build index. No guessed or prerelease URL was substituted.')
        url = min(releases[version], key=lambda item: (item[0], len(item[1]), item[1]))[1]
        return version, url, None

    def resolve(self, name: str, progress: Progress, latest: bool = False) -> dict:
        if name == 'lsfg':
            version, url, expected = self._resolve_lsfg(progress, latest)
        elif name == 'opti':
            progress('Resolving the latest stable OptiScaler release', .01)
            try:
                d = get_json(OPTI_API)
            except FusionError as error:
                # GitHub's release pages remain usable when the anonymous API is rate-limited.
                if 'HTTP 403' not in str(error) and 'HTTP 429' not in str(error): raise
                page = self.cache / 'opti-latest.html'
                meta = download('https://github.com/optiscaler/OptiScaler/releases/latest', page, lambda *_: None, limit=8*1024*1024)
                tag = meta['final_url'].rsplit('/', 1)[-1]
                if not re.fullmatch(r'v?\d+\.\d+\.\d+', tag):
                    raise FusionError('Cannot confirm a stable OptiScaler release from the official release page.')
                assets_page = self.cache / 'opti-assets.html'
                download(f'https://github.com/optiscaler/OptiScaler/releases/expanded_assets/{tag}', assets_page, lambda *_: None, limit=8*1024*1024)
                links = re.findall(r'href=[\"\']([^\"\']+/releases/download/[^\"\']+)[\"\']', assets_page.read_text('utf-8'))
                d = {'tag_name': tag, 'assets': [{'name': urllib.parse.unquote(link.rsplit('/', 1)[-1]),
                     'browser_download_url': urllib.parse.urljoin('https://github.com', html.unescape(link))} for link in links]}
            if d.get('draft') or d.get('prerelease'): raise FusionError('Upstream latest release is not stable.')
            version = str(d.get('tag_name', ''))
            assets = [a for a in d.get('assets', []) if a['name'].lower().endswith(('.7z', '.zip'))
                      and 'opti' in a['name'].lower() and not any(x in a['name'].lower() for x in ('pdb', 'debug', 'symbols', 'source'))]
            if not assets: raise FusionError('No supported OptiScaler release archive was found. Upstream packaging may have changed.')
            assets.sort(key=lambda a: (not a['name'].lower().endswith('.zip'), a['name']))
            asset = assets[0]; url = asset['browser_download_url']; expected = asset.get('digest')
            if expected and not expected.startswith('sha256:'): expected = None
        elif name == 'fsr4fix':
            progress('Resolving pinned community FSR 4.1.1b RDNA2 fix', .01)
            version, url, expected = FSR4FIX['version'], FSR4FIX['url'], FSR4FIX['sha256']
        elif name == 'reshade':
            progress('Resolving the official standard ReShade installer', .01)
            page = self.cache / 'reshade-page.html'
            download(RESH_SITE, page, lambda *_: None, limit=4*1024*1024)
            urls = re.findall(r'''(?:https://(?:www\.)?reshade\.me)?/downloads/ReShade_Setup_(\d+\.\d+\.\d+)\.exe''', page.read_text('utf-8'))
            if not urls: raise FusionError('The official ReShade download link was not found. No mirror or add-on build was substituted.')
            version = max(urls, key=lambda v: tuple(map(int, v.split('.'))))
            url, expected = f'https://reshade.me/downloads/ReShade_Setup_{version}.exe', None
        else: raise FusionError('Unknown component.')
        if not re.fullmatch(r'[A-Za-z0-9._+-]{1,80}', version): raise FusionError('Unsafe upstream version identifier.')
        checked_url(url)
        return {'component': name, 'version': version, 'url': url, 'expected': expected}

    def check_updates(self, progress: Progress) -> dict:
        current = self.status()
        results = {}
        for i, name in enumerate(('lsfg', 'opti', 'reshade')):
            progress(f'Checking {name} for updates', i / 3)
            try:
                release = self.resolve(name, progress, latest=True)
                installed = current.get(name, {}).get('version')
                results[name] = {**release, 'installed': installed,
                                 'different': (installed or '').lstrip('v') != release['version'].lstrip('v')}
            except FusionError as error:
                results[name] = {'error': str(error), 'installed': current.get(name, {}).get('version')}
        atomic_json(self.root / 'update-check.json', results)
        return results

    def install(self, name: str, progress: Progress, latest: bool = False) -> dict:
        release = self.resolve(name, progress, latest=latest)
        version, url, expected = release['version'], release['url'], release['expected']
        archive = self.cache / (name + '-' + version + '-' + url.rsplit('/', 1)[-1])
        meta = download(url, archive, progress, expected)
        meta['source'] = 'download'
        meta['archive'] = str(archive)
        return self.install_archive(name, version, archive, meta, progress)

    def install_archive(self, name: str, version: str, archive: Path, meta: dict, progress: Progress) -> dict:
        if name not in ('lsfg', 'opti', 'reshade', 'fsr4fix') or not re.fullmatch(r'[A-Za-z0-9._+-]{1,80}', version):
            raise FusionError('Invalid component or package version.')
        if sha256(archive) != meta.get('sha256'):
            raise FusionError(f'{name}: package integrity check failed. The cache was not changed.')
        if name == 'fsr4fix' and (version != FSR4FIX['version'] or meta.get('sha256') != FSR4FIX['sha256']):
            raise FusionError('The RDNA2 fix must match the pinned FSR 4.1.1b release and SHA-256.')
        progress(f'Extracting {name} {version}', .88)
        stage = Path(tempfile.mkdtemp(prefix='.package-', dir=self.packages))
        try:
            extract(archive, stage)
            if name == 'lsfg':
                manifests = []
                for f in stage.rglob('*.json'):
                    try:
                        j = json.loads(f.read_text())
                        if 'lsfg' in str(j.get('layer', {}).get('name', '')).lower(): manifests.append(f)
                    except (ValueError, OSError): pass
                if not manifests: raise FusionError('The lsfg-vk package contains no recognized Vulkan layer manifest.')
                so = list(stage.rglob('*lsfg*.so*'))
                if not so: raise FusionError('The lsfg-vk package contains no shared library.')
                # Prefer the 64-bit layer; 32-bit support is only reported if an actual ELF32 library is bundled.
                so64 = [p for p in so if p.is_file() and p.read_bytes()[:5] == b'\x7fELF\x02']
                if not so64: raise FusionError('No x86-64 LSFG library in the release archive.')
                payload = {'manifest': str(manifests[0].relative_to(stage)), 'library': str(so64[0].relative_to(stage)),
                           'supports_32bit': any(p.is_file() and p.read_bytes()[:5] == b'\x7fELF\x01' for p in so)}
            elif name == 'opti':
                candidates = [p for p in stage.rglob('*') if p.name.lower() == 'optiscaler.dll']
                if not candidates: raise FusionError('OptiScaler.dll is missing from the archive.')
                dll = min(candidates, key=lambda p: len(p.parts))
                ini = next((p for p in dll.parent.iterdir() if p.name.lower() == 'optiscaler.ini'), None)
                if ini is None: raise FusionError('The official OptiScaler.ini is missing.')
                payload = {'directory': str(dll.parent.relative_to(stage)), 'dll': dll.name, 'ini': ini.name}
            elif name == 'fsr4fix':
                from fusion_steam import pe_info
                candidates = [p for p in stage.rglob('*') if p.is_file() and not p.is_symlink() and p.name.lower() == FSR4FIX['dll']]
                if len(candidates) != 1:
                    raise FusionError('The RDNA2 fix archive must contain exactly one FidelityFX upscaler DLL.')
                dll = candidates[0]; info = pe_info(dll)
                if info['kind'] != 'pe' or info['bits'] != 64:
                    raise FusionError('The RDNA2 fix is not a 64-bit Windows DLL.')
                payload = {'dll': str(dll.relative_to(stage)), 'dll_sha256': sha256(dll)}
            else:
                bins = {p.name.lower(): str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file() and p.name.lower() in ('reshade32.dll', 'reshade64.dll')}
                if 'reshade64.dll' not in bins: raise FusionError('No ReShade64.dll was found in the installer payload. The Windows installer was not executed.')
                payload = {'binaries': bins}
            # Unique generation directories avoid replacing libraries still mapped by a running game.
            final = self.packages / f'{name}-{version}-{meta["sha256"][:12]}'
            if name == 'fsr4fix': final = self.packages / f'{name}-{version}-{meta["sha256"][:12]}-{time.time_ns()}'
            if final.exists(): shutil.rmtree(stage)
            else: os.replace(stage, final)
            info = {'version': version, 'path': str(final), 'payload': payload, **meta}
            progress(f'{name} {version} ready', 1.)
            return self._record(name, info)
        finally:
            if stage.exists(): shutil.rmtree(stage)

    def _bundle_manifest(self):
        if not self.bundled: return {}
        try:
            manifest = read_json(self.bundled / 'manifest.json', {})
            if not isinstance(manifest, dict) or not isinstance(manifest.get('components', {}), dict):
                raise FusionError('The offline bundle manifest is invalid.')
            return manifest
        except (FusionError, OSError) as error:
            message = str(error)
            if message not in self._bundle_errors: self._bundle_errors.append(message)
            return {}

    def bundle_status(self) -> dict:
        manifest = self._bundle_manifest()
        entries = manifest.get('components', {})
        ready, missing = [], []
        for name in ('lsfg', 'opti', 'reshade', 'standard', 'sweetfx', 'fxshaders'):
            entry = entries.get(name)
            try:
                if not isinstance(entry, dict) or not self.bundled:
                    missing.append(name); continue
                path = safe_target(self.bundled, entry['archive'])
                if path.is_file(): ready.append(name)
                else: missing.append(name)
            except (FusionError, OSError, KeyError, TypeError) as error:
                missing.append(name)
                message = f'{name}: {error}'
                if message not in self._bundle_errors: self._bundle_errors.append(message)
        return {'complete': not missing and not self._bundle_errors, 'available': ready, 'missing': missing,
                'errors': list(self._bundle_errors),
                'note': manifest.get('note', 'No offline tool archives are included in this build.')}

    def seed_bundled(self, progress: Progress, retry: bool = False) -> dict:
        """Seed absent tools from verified local archives only, never from the network.

        Cache paths live outside the plugin directory so Decky replacement does not
        strand a game's mapped library or launcher. Existing/downloaded generations
        win over the bundled baseline. No game files are changed by this operation.
        """
        if self._seed_attempted and not retry: return self.bundle_status()
        self._seed_attempted = True
        self._bundle_errors = []
        manifest = self._bundle_manifest()
        for name, entry in manifest.get('components', {}).items():
            try:
                if name not in ('lsfg', 'opti', 'reshade', 'standard', 'sweetfx', 'fxshaders'):
                    raise FusionError('Unknown bundled component.')
                current = self.status()
                existing = current.get('shaders', {}).get(name) if name in ('standard', 'sweetfx', 'fxshaders') else current.get(name)
                if isinstance(existing, dict) and existing.get('path') and Path(existing['path']).is_dir():
                    continue  # No silent downgrades or changes to an installed generation.
                source = safe_target(self.bundled, entry['archive'])
                digest = entry.get('sha256', '')
                if not re.fullmatch(r'[a-f0-9]{64}', digest) or not source.is_file() or sha256(source) != digest:
                    raise FusionError(f'Bundled {name} is missing or its SHA-256 does not match. Reinstall the complete ZIP.')
                meta = {k: v for k, v in entry.items() if k not in ('payload', 'path', 'archive', 'source')}
                meta.update({'source': 'bundle', 'archive': str(source), 'sha256': digest})
                if name in ('lsfg', 'opti', 'reshade'):
                    self.install_archive(name, entry['version'], source, meta, progress)
                else:
                    self._install_shader_archive(name, entry['repository'], entry['commit'], source, meta, progress)
            except (FusionError, OSError, KeyError, ValueError, TypeError) as error:
                self._bundle_errors.append(f'{name}: {error}')
        return self.bundle_status()

    def install_shader_pack(self, pack_id: str, progress: Progress, repository: str = '', branch: str = '') -> dict:
        known = next((p for p in SHADER_PACKS if p['id'] == pack_id), None)
        if known:
            repository, branch = known['repo'], known['branch']
        elif pack_id == 'custom':
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository): raise FusionError('Use a GitHub owner/repository, not an arbitrary URL.')
            if not branch: branch = get_json('https://api.github.com/repos/' + repository)['default_branch']
            pack_id = 'custom-' + hashlib.sha256(repository.encode()).hexdigest()[:12]
        else: raise FusionError('Unknown shader pack.')
        ref = urllib.parse.quote(branch, safe='')
        commit = get_json(f'https://api.github.com/repos/{repository}/commits/{ref}').get('sha', '')
        if not re.fullmatch('[0-9a-f]{40}', commit): raise FusionError('Unable to pin the shader pack to an upstream commit.')
        url = f'https://codeload.github.com/{repository}/zip/{commit}'
        archive = self.cache / f'{pack_id}-{commit[:12]}.zip'
        meta = download(url, archive, progress)
        meta.update({'source': 'download', 'archive': str(archive)})
        return self._install_shader_archive(pack_id, repository, commit, archive, meta, progress)

    def _install_shader_archive(self, pack_id, repository, commit, archive, meta, progress):
        known = next((p for p in SHADER_PACKS if p['id'] == pack_id), None)
        if not re.fullmatch(r'[a-z0-9-]{1,80}', pack_id) or not re.fullmatch('[0-9a-f]{40}', commit):
            raise FusionError('Invalid shader package identifier or commit.')
        if sha256(archive) != meta.get('sha256'): raise FusionError('Shader archive integrity check failed.')
        stage = Path(tempfile.mkdtemp(prefix='.shader-', dir=self.packages))
        try:
            extract(archive, stage)
            dirs = [p for p in stage.iterdir() if p.is_dir()]
            base = dirs[0] if len(dirs) == 1 else stage
            # The extracted repository is trusted as shader source, never as executable code.
            shader_dirs = [p for p in base.rglob('*') if p.is_dir() and p.name.lower() == 'shaders']
            if not shader_dirs and not list(base.rglob('*.fx')) and not list(base.rglob('*.fxh')):
                raise FusionError('The selected repository contains no ReShade shader source.')
            final = self.packages / f'shaders-{pack_id}-{commit[:12]}'
            relative_base = base.relative_to(stage)
            if final.exists(): shutil.rmtree(stage)
            else: os.replace(stage, final)
            info = {'id': pack_id, 'name': known['name'] if known else repository, 'repository': repository,
                    'commit': commit, 'path': str(final / relative_base), **meta}
            status = self.status(); status.setdefault('shaders', {})[pack_id] = info
            atomic_json(self.root / 'packages.json', status)
            progress('Shader pack ready', 1.)
            return info
        finally:
            if stage.exists(): shutil.rmtree(stage)
