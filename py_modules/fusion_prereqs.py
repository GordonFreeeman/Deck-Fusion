"""Opt-in prefix maintenance through Protontricks. No Microsoft binaries shipped.

All paths come from the installed game and live launch text. No generic shell or
Winetricks verb API is exposed. Snapshot/restore preserves symlinks, not their
external targets (which may contain saves). Receipts are not GPU/mod verdicts.
"""
from __future__ import annotations
from contextlib import contextmanager
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shlex
import shutil
import signal
import stat
import struct
import subprocess
import time
import uuid

from fusion_launch import launch_assignments
from fusion_steam import running_game, steam_roots, libraries, pe_info
from fusion_util import FusionError, atomic_json, read_json, safe_target, sha256
from fusion_wine import inspect_overrides

APP = 'com.github.Matoking.protontricks'
VERBS = ('d3dcompiler_47', 'vcrun2022')
MAX_LOG = 4 * 1024 * 1024
SESSION_KEYS = ('DISPLAY', 'XAUTHORITY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS')
WINETRICKS_SHA256 = '672a1ff4442e8691a3ffc0e6860137e201a1d1227e9b3044245f1731e9e9837e'
VC_MIN_VERSION = (14, 44, 0, 0)


def native_vc_version(path, bits):
    """Conservative local evidence, not a signature/authenticity verifier."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16*1024*1024: return None
        info = pe_info(path)
        if info['kind'] != 'pe' or info['bits'] != bits: return None
        data = path.read_bytes()
        if b'Wine builtin DLL' in data[:256] or b'Wine placeholder DLL' in data[:256] or 'Microsoft Corporation'.encode('utf-16le') not in data: return None
        # VERSIONINFO's VS_FIXEDFILEINFO has a fixed signature and structure version.
        key = 'VS_VERSION_INFO\0'.encode('utf-16le')
        start = data.find(key)
        if start < 6: return None
        offset = (start + len(key) + 3) & ~3
        signature, version, ms, ls = struct.unpack_from('<4I', data, offset)
        if signature != 0xFEEF04BD or version != 0x10000: return None
        return (ms >> 16, ms & 65535, ls >> 16, ls & 65535) if ms >> 16 == 14 else None
    except (OSError, ValueError, struct.error): return None


def vc_runtime_evidence(prefix, bits):
    if bits not in (32, 64): return {'satisfied': False, 'native_versions': {}}
    try:
        reg = prefix / 'system.reg'
        if not reg.is_file() or reg.is_symlink() or reg.stat().st_size > 24*1024*1024: return {'satisfied': False, 'native_versions': {}}
        text = reg.read_text(errors='replace')
        is64 = '#arch=win64' in text
        folder = 'system32' if bits == 64 or not is64 else 'syswow64'
        dlls = ['vcruntime140.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'msvcp140_atomic_wait.dll']
        if bits == 64: dlls.append('vcruntime140_1.dll')
        versions = {name: native_vc_version(prefix / 'drive_c/windows' / folder / name, bits) for name in dlls}
        # Steam/common redists write Microsoft's installed version independently of Winetricks.
        arch = 'x64' if bits == 64 else 'x86'
        registered = False
        for block in re.split(r'(?m)(?=^\[)', text):
            header = block.split('\n', 1)[0].replace('\\\\', '\\').casefold()
            if not re.match(r'^\[software\\(?:wow6432node\\)?microsoft\\visualstudio\\14\.0\\vc\\runtimes\\' + arch + r'\]', header): continue
            installed = re.search(r'(?im)^"Installed"=dword:0*1\s*$', block)
            value = re.search(r'(?im)^"Version"="v?(\d+)\.(\d+)\.(\d+)\.(\d+)"', block)
            if installed and value and int(value[1]) == 14 and tuple(map(int, value.groups())) >= VC_MIN_VERSION: registered = True
        return {'satisfied': registered and all(v and v >= VC_MIN_VERSION for v in versions.values()),
                'native_versions': versions, 'registered': registered, 'architecture': bits}
    except OSError: return {'satisfied': False, 'native_versions': {}}


def steam_session_environment(env, uid, procroot=Path('/proc')):
    """Fill missing service-session fields from this user's live Steam client.

    Decky's service can lack the display and session bus used by Windows setup.
    Copy only these five fields, never Steam's injection or Wine environment.
    Keep an existing display context; do not mix credentials across sessions.
    """
    env = dict(env)
    try: processes = sorted(procroot.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else -1)
    except OSError: return env
    for proc in processes:
        if not proc.name.isdigit(): continue
        try:
            if proc.stat().st_uid != uid: continue
            if (proc / 'exe').resolve(strict=True).name not in ('steam', 'steamwebhelper'): continue
            with (proc / 'environ').open('rb') as stream: raw = stream.read(65536)
            session = {}
            for field in raw.split(b'\0'):
                key, separator, value = field.partition(b'=')
                if separator and key.decode('ascii', 'ignore') in SESSION_KEYS and value:
                    session[key.decode('ascii')] = value.decode('utf-8', 'strict')
            if not session.get('DISPLAY') and not session.get('WAYLAND_DISPLAY'): continue
            if any(env.get(key) and env[key] != session.get(key) for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR')): continue
            for key in SESSION_KEYS:
                if not env.get(key) and session.get(key): env[key] = session[key]
            break
        except (OSError, UnicodeError): continue
    return env


def installer_error(code, tail, log):
    tail = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', tail)
    tail = ''.join(c for c in tail if c in '\n\t' or ord(c) >= 32).strip()[-12000:]
    low = tail.lower()
    hint = ''
    if 'sha256sum mismatch' in low or 'sha1sum mismatch' in low or 'checksum mismatch' in low:
        hint = 'Winetricks rejected a download checksum. Update Protontricks/Winetricks and retry; do not bypass the checksum.'
    elif ('nodrv_createdevice' in low or 'cannot open display' in low or 'could not open display' in low or
          'make sure that your x server is running' in low):
        hint = 'The Windows installer could not connect to the display session. Retry from Deck Fusion in Desktop Mode.'
    elif 'bwrap:' in low and ('operation not permitted' in low or 'permission denied' in low):
        hint = 'Protontricks could not start its Steam Runtime container. Update the Protontricks helper and retry.'
    elif 'conflicts with' in low and 'vcrun' in low:
        hint = 'Winetricks reports a conflicting Visual C++ runtime. Keep the snapshot; review the installed runtime before replacing it.'
    elif any(x in low for x in ('0x80070666', 'another version of this product is already installed', 'exit status 1638')):
        hint = 'Microsoft setup found another Visual C++ version. Deck Fusion checks registered native DLL versions before installing; this prefix did not pass that check. The original prefix snapshot is retained.'
    elif 'unknown arg' in low or 'unknown verb' in low:
        hint = 'The installed Winetricks does not recognize a requested option or runtime. Update Protontricks/Winetricks and retry.'
    return (f'Prefix tool exited with status {code}. The prefix snapshot is retained.\n' +
            (hint + '\n' if hint else '') + f'Runtime log: {log}\n\nInstaller output:\n' +
            (tail or 'The tool produced no output.'))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cancelled(event):
    if event and event.is_set():
        raise FusionError('Runtime operation cancelled. Any completed prefix snapshot is retained. Inspect the receipt before launching or retrying.')


def prefix_inventory(root: Path, hashes=False, event=None):
    """Do not follow Wine's z: drive, user-folder links or builtin-DLL links."""
    result = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            cancelled(event)
            path = Path(folder) / name
            info = path.lstat()
            rel = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                result[rel] = {'type': 'link', 'target': os.readlink(path)}
            elif stat.S_ISDIR(info.st_mode):
                result[rel] = {'type': 'dir'}
            elif stat.S_ISREG(info.st_mode):
                result[rel] = {'type': 'file', 'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
                if hashes: result[rel]['sha256'] = sha256(path)
            else:
                raise FusionError(f'Prefix contains a socket/device/special file: {rel}. Close Wine before maintenance.')
            if len(result) > 150000:
                raise FusionError('Prefix scan exceeded 150,000 entries. No automatic maintenance was started.')
    return result


def content_index(index):
    return {key: {k: v for k, v in item.items() if k != 'mtime_ns'} for key, item in index.items()}


def prefix_processes(prefix: Path, appid: str, procroot=Path('/proc')):
    found = []
    own = os.geteuid()
    for proc in procroot.iterdir():
        if not proc.name.isdigit() or proc.name == str(os.getpid()): continue
        try:
            if proc.stat().st_uid != own: continue
            args = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
            if not args: continue
            env = {}
            for field in (proc / 'environ').read_bytes().split(b'\0'):
                key, sep, value = field.partition(b'=')
                if sep: env[key.decode('utf-8', 'replace')] = value.decode('utf-8', 'replace')
            wine = env.get('WINEPREFIX', '')
            compat = env.get('STEAM_COMPAT_DATA_PATH', '')
            matching = (wine and Path(wine).resolve() == prefix) or (compat and (Path(compat) / 'pfx').resolve() == prefix)
            app_match = appid in (env.get('SteamAppId'), env.get('SteamGameId'), env.get('STEAM_APPID'))
            if matching or (app_match and re.search(r'proton|wine|\.exe(?:\s|$)', args, re.I)):
                found.append({'pid': int(proc.name), 'command': args[:200]})
        except (FileNotFoundError, ProcessLookupError): continue
        except PermissionError:
            # Unknown other-session processes are not evidence of this prefix.
            continue
        except OSError: continue
    return found


class PrefixRuntimes:
    def __init__(self, engine):
        self.e = engine

    def user_check(self):
        if os.geteuid() == 0:
            raise FusionError('Prefix tools must run as the Deck user, not root. Deck Fusion does not request root privileges.')
        if self.e.home.stat().st_uid != os.geteuid():
            raise FusionError('The backend user does not own the selected Steam home. No prefix tool was executed.')

    def environment(self):
        env = dict(os.environ)
        if self.e.home.stat().st_uid == os.geteuid():
            env = steam_session_environment(env, os.geteuid())
        # Do not accidentally inject graphics layers or apply a different Wine
        # installation to Microsoft's installer. Keep desktop/session credentials.
        for key in list(env):
            if (key.startswith(('WINE', 'WINETRICKS', 'PROTON', 'STEAM_COMPAT', 'LSFG', 'DXVK_', 'VKD3D_')) or
                key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'VK_INSTANCE_LAYERS', 'VK_LAYER_PATH', 'VK_ADD_LAYER_PATH',
                        'DECK_FUSION_LSFG', 'STEAM_RUNTIME', 'SteamAppId', 'SteamGameId', 'STEAM_APPID')):
                env.pop(key, None)
        env.update(HOME=str(self.e.home), WINETRICKS_GUI='none',
                   PATH=f'{self.e.home}/.local/bin:/usr/local/bin:/usr/bin:/bin')
        return env

    def _probe(self, command, timeout=8):
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, env=self.environment(), timeout=timeout, check=False)
            return result.returncode, result.stdout[-12000:]
        except (OSError, subprocess.TimeoutExpired) as error: return -1, str(error)

    def helper(self):
        path = self.environment()['PATH']
        flatpak = shutil.which('flatpak', path=path)
        if flatpak:
            code, location = self._probe([flatpak, 'info', '--show-location', APP])
            if code == 0:
                return {'kind': 'flatpak', 'executable': flatpak, 'location': location.strip(), 'available': True}
        native = shutil.which('protontricks', path=path)
        tricks = shutil.which('winetricks', path=path)
        if native and tricks:
            return {'kind': 'native', 'executable': native, 'winetricks': tricks, 'available': True}
        return {'kind': 'missing', 'available': False, 'flatpak': flatpak,
                'note': 'Install the official Protontricks Flatpak helper. A native installation also needs Winetricks.'}

    def target(self, payload):
        if not isinstance(payload, dict): raise FusionError('Invalid runtime request.')
        appid = str(payload.get('appid', ''))
        game = self.e.game(appid)
        exe = payload.get('exe')
        if not isinstance(exe, str) or not exe:
            raise FusionError('Select the game’s Windows executable in Library before prefix maintenance.')
        root = Path(game['root']).resolve()
        path = Path(exe)
        if not path.is_absolute(): path = root / path
        if not path.is_relative_to(root): raise FusionError('Executable is outside this game installation.')
        path = safe_target(root, path.relative_to(root).as_posix())
        if not path.is_file():
            raise FusionError('The selected game executable no longer exists. Refresh Library.')
        image = pe_info(path)
        if image['kind'] != 'pe' or image['bits'] not in (32, 64):
            raise FusionError('Windows runtime setup needs a 32-bit or 64-bit Windows executable and its initialized Proton prefix. Native Linux games and emulator programs do not use these Windows dependencies; select the Windows build only when you intend to run it through Proton.')
        launch = payload.get('launch', '')
        if not isinstance(launch, str) or len(launch) > 32768: raise FusionError('Invalid launch text.')
        context = inspect_overrides(self.e, {'appid': appid, 'exe': str(path), 'wine': {}}, launch)
        prefixes = context['prefixes']
        selected = payload.get('prefix')
        if selected and selected not in prefixes:
            raise FusionError('The selected prefix is not among the detected prefixes for this game. Refresh the runtime inspection.')
        selected = selected or (prefixes[0] if len(prefixes) == 1 else None)
        notes = list(context['warnings'])
        # Protontricks obtains the selected compatibility tool from Steam, not
        # a guessed Proton path or system Wine. Explicit runner overrides cannot
        # be silently discarded by this workflow.
        assignments = launch_assignments(launch)
        unsupported = [key for key in ('WINE', 'WINESERVER', 'PROTON_VERSION', 'STEAM_COMPAT_TOOL_PATHS', 'STEAM_COMPAT_CLIENT_INSTALL_PATH') if assignments.get(key)]
        if unsupported:
            raise FusionError('Custom runner overrides need manual handling: ' + ', '.join(unsupported) + '. This workflow follows the compatibility tool selected in Steam, rather than guessing another Wine/Proton build.')
        if assignments.get('WINEPREFIX') and not assignments.get('STEAM_COMPAT_DATA_PATH'):
            notes.append('WINEPREFIX-only launch customization detected. The runtime operation will explicitly bind Protontricks to this detected pfx directory.')
        return {'appid': appid, 'game': game['name'], 'exe': str(path), 'root': str(root),
                'prefixes': prefixes, 'prefix': selected, 'notes': notes, 'assignments': assignments,
                'launch': launch}

    def validate_prefix(self, target):
        if not target['prefix']:
            raise FusionError('Select one detected Proton prefix. If none exists, launch the game once using its intended Proton version, then close it and refresh.')
        prefix = Path(target['prefix'])
        if prefix.name != 'pfx' or not prefix.is_dir() or prefix.is_symlink():
            raise FusionError('A complete Proton pfx directory is required; arbitrary Wine folders are not modified.')
        for name in ('system.reg', 'user.reg'):
            f = prefix / name
            if not f.is_file() or f.is_symlink(): raise FusionError(f'The selected prefix lacks a regular {name}. It may be incomplete.')
        for name in ('drive_c', 'drive_c/windows', 'drive_c/windows/system32'):
            if not safe_target(prefix, name).is_dir(): raise FusionError('The selected prefix has no complete Windows system directory.')
        if not (prefix.parent / 'pfx.lock').is_file():
            raise FusionError('Proton has not initialized this prefix (pfx.lock is missing). Start the game with the chosen Proton version once first.')
        return prefix

    def idle(self, target):
        if (self.e.store(target['appid']) / 'pending.json').exists():
            raise FusionError('Finish or recover the pending graphics-file transaction in Apply before changing runtimes.')
        if running_game(Path(target['exe']), target['appid'])['running']:
            raise FusionError(f"Close {target['game']} before changing its prefix.")
        processes = prefix_processes(Path(target['prefix']), target['appid'])
        if processes:
            raise FusionError('The selected prefix still has active Proton/Wine processes: ' +
                              ', '.join(str(x['pid']) for x in processes) + '. Close the game and Protontricks, wait a moment, then retry. Other games are not terminated.')

    def evidence(self, prefix, bits=64):
        if not prefix: return []
        prefix = Path(prefix)
        log = prefix / 'winetricks.log'
        receipt = log.read_text(errors='replace')[-262144:].splitlines() if log.is_file() and log.stat().st_size < 4*1024*1024 else []
        result = []
        for name, dlls in (('d3dcompiler_47', ('d3dcompiler_47.dll',)),
                           ('vcrun2022', ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'))):
            files = []
            for arch in ('system32', 'syswow64'):
                for dll in dlls:
                    f = prefix / 'drive_c/windows' / arch / dll
                    files.append({'path': f'drive_c/windows/{arch}/{dll}', 'present': f.is_file(), 'symlink': f.is_symlink()})
            result.append({'name': name, 'recorded': name in receipt, 'files': files,
                           'note': 'A Winetricks receipt or file presence is not proof of native provenance, correct version or successful game/mod initialization.'})
            if name == 'vcrun2022':
                result[-1].update(vc_runtime_evidence(prefix, bits))
                result[-1]['note'] = ('Compatible Visual C++ runtime detected for this executable. Installation will be skipped.' if result[-1]['satisfied'] else
                    'No complete compatible native Visual C++ runtime was verified. A Winetricks receipt alone is insufficient.')
            else: result[-1]['satisfied'] = name in receipt and any(f['present'] and not f['symlink'] for f in files)
        return result

    def validate_record(self, record, target, same_prefix=False):
        if (not isinstance(record, dict) or not re.fullmatch('[0-9a-f]{32}', str(record.get('id', ''))) or
            record.get('appid') != target['appid'] or not isinstance(record.get('prefix'), str) or
            not Path(record['prefix']).is_absolute() or Path(record['prefix']).name != 'pfx' or
            (same_prefix and record['prefix'] != target['prefix'])):
            raise FusionError('Invalid runtime receipt. No untrusted receipt path was opened or restored.')
        return dict(record)

    def log_tail(self, root, relative):
        path = safe_target(root, relative)
        if not path.is_file(): return None
        with path.open('rb') as f:
            f.seek(max(0, path.stat().st_size - 16000))
            return {'path': str(path), 'text': f.read(16000).decode('utf-8', 'replace')}

    def status(self, payload):
        target = self.target(payload)
        blockers = []
        try:
            self.user_check(); self.validate_prefix(target); self.idle(target)
        except FusionError as error: blockers.append(str(error))
        receipt = snapshot = helper_log = None
        store = self.e.store(target['appid'])
        try:
            raw = read_json(safe_target(store, 'runtime-last.json'), None)
            if raw is not None:
                receipt = self.validate_record(raw, target)
                log = self.log_tail(store, 'runtime-jobs/' + receipt['id'] + '/installer.log')
                receipt['log_tail'] = log['text'] if log else ''
            snapshot = self.snapshot_record(target)
            helper_log = self.log_tail(self.e.data, 'protontricks-helper.log')
        except FusionError as error: blockers.append(str(error))
        return {**{k: target[k] for k in ('appid', 'game', 'exe', 'prefixes', 'prefix', 'notes')},
                'helper': self.helper(), 'runtimes': self.evidence(target['prefix'], pe_info(Path(target['exe']))['bits']), 'blockers': blockers,
                'last': receipt, 'restore_snapshot': snapshot, 'helper_log': helper_log,
                'note': 'These optional Windows libraries belong inside the selected game’s Proton prefix, not its game folder. This operation does not repair or replace mod-loader DLLs.'}

    def options(self, payload):
        verbs = payload.get('runtimes', list(VERBS))
        if not isinstance(verbs, list) or not verbs or any(v not in VERBS for v in verbs):
            raise FusionError('Choose d3dcompiler_47 and/or vcrun2022. Other Winetricks verbs are not allowed.')
        if payload.get('force_vc', False) is not False:
            raise FusionError('Winetricks --force is not exposed because it also bypasses download checksum failures. Runtime errors must be resolved without silently weakening verification.')
        return [x for x in VERBS if x in verbs], False

    def _plan(self, payload, restoring=False):
        self.user_check()
        target = self.target(payload); prefix = self.validate_prefix(target); self.idle(target)
        index = prefix_inventory(prefix)
        size = sum(x.get('size', 0) for x in index.values())
        free = shutil.disk_usage(prefix.parent).free
        helper = self.helper()
        verbs, force = ([], False) if restoring else self.options(payload)
        if not restoring and not helper['available']: raise FusionError('Install Protontricks using the separate helper button first.')
        # Validate the compatibility-tool path before making any snapshot.
        if not restoring: self.command(target, helper, verbs)
        record = manifest = None
        copy_bytes = size
        if restoring:
            record = self.snapshot_record(target)
            if not record or not record.get('snapshot_ready'):
                raise FusionError('No completed snapshot for this selected prefix is available.')
            if record.get('state') == 'restored': raise FusionError('This snapshot has already been restored. The displaced prefix remains retained.')
            _, manifest = self.snapshot_manifest(target, record)
            copy_bytes = sum(x.get('size', 0) for x in manifest.values())
        # Runtime downloads/extraction may require additional space beyond this
        # minimum; tool failures retain the snapshot and report their logs.
        required_space = copy_bytes + 256*1024*1024
        if free < required_space:
            raise FusionError(f'Not enough free space for the prefix copy and workspace. Need at least {required_space//1048576} MiB on the prefix filesystem.')
        plan = {'target': target, 'helper': helper, 'runtimes': verbs, 'force_vc': force,
                'prefix_bytes': size, 'copy_bytes': copy_bytes, 'required_space_bytes': required_space,
                'free_bytes': free, 'inventory': fingerprint(index),
                'snapshot_index': fingerprint(manifest) if manifest else None,
                'filesystem_grants': self.filesystem_grants(target) if not restoring and helper['kind'] == 'flatpak' else [],
                'restoring': restoring, 'snapshot_id': record['id'] if record else None,
                'snapshot': str(prefix.parent / '.deck-fusion-runtime-backups'),
                'warnings': ['Close the game and any Protontricks windows. Do not launch the game or change its Proton selection during this operation.',
                    'Downloads and runtime installers can fail or change existing VC components. A full pfx snapshot is retained first; external symlink targets are not copied.',
                    'No mods, Steam launch options or graphics profiles are changed. Missing dependencies are only one possible cause of a game that will not launch.']}
        if restoring:
            plan['warnings'].append('Restore reverts all files in pfx, including prefix-local settings and saves since the snapshot. The entire current pfx is retained at a separate path; external symlink targets are untouched.')
        # Free disk space fluctuates independently of the approved operation.
        # Recheck it on execution, but do not invalidate approval for unrelated IO.
        plan['approval'] = fingerprint({k:v for k,v in plan.items() if k != 'free_bytes'})
        return plan

    def plan(self, payload): return self._plan(payload, payload.get('restore') is True)

    @contextmanager
    def maintenance_lock(self, appid):
        store = self.e.store(appid); store.mkdir(parents=True, exist_ok=True)
        with (store / 'prefix-maintenance.lock').open('a+') as lock:
            try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise FusionError('Another prefix-maintenance operation is in progress.')
            try: yield
            finally: fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _save(self, record):
        store = self.e.store(record['appid'])
        atomic_json(store / 'runtime-jobs' / record['id'] / 'receipt.json', record)
        atomic_json(store / 'runtime-last.json', record)
        if record.get('snapshot_ready'):
            index = read_json(store / 'runtime-snapshots.json', {})
            index[record['prefix']] = record
            atomic_json(store / 'runtime-snapshots.json', index)

    def snapshot_record(self, target):
        store = self.e.store(target['appid'])
        index = read_json(safe_target(store, 'runtime-snapshots.json'), {})
        if not isinstance(index, dict): raise FusionError('Invalid runtime snapshot index.')
        record = index.get(target.get('prefix', ''))
        return self.validate_record(record, target, same_prefix=True) if record is not None else None

    def snapshot_manifest(self, target, record):
        record = self.validate_record(record, target, same_prefix=True)
        folder = safe_target(Path(target['prefix']).parent, '.deck-fusion-runtime-backups/' + record['id'])
        snapshot = safe_target(folder, 'pfx')
        expected = read_json(safe_target(folder, 'index.json'), None)
        if not snapshot.is_dir() or not isinstance(expected, dict) or not expected:
            raise FusionError('The saved prefix snapshot has no valid integrity index.')
        for rel, item in expected.items():
            # These are Linux prefix paths, not Windows archive members. Wine's
            # literal dosdevices/c: and z: symlinks must remain valid names.
            if (not isinstance(rel, str) or not rel or '\x00' in rel or
                PurePosixPath(rel).is_absolute() or '..' in PurePosixPath(rel).parts or
                PurePosixPath(rel).as_posix() != rel):
                raise FusionError('Invalid relative path in snapshot integrity index.')
            if not isinstance(item, dict) or item.get('type') not in ('file', 'dir', 'link'):
                raise FusionError('Invalid snapshot integrity entry.')
            if item['type'] == 'file' and (type(item.get('size')) is not int or item['size'] < 0 or
                not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', '')))):
                raise FusionError('Invalid snapshot file size or checksum.')
            if item['type'] == 'link' and not isinstance(item.get('target'), str):
                raise FusionError('Invalid snapshot link entry.')
        return snapshot, expected

    def filesystem_grants(self, target):
        # Scope these grants to this invocation. Protontricks needs to read game
        # manifests and locate Proton/Steam Runtime, including separate libraries.
        # Do not create permanent Flatpak overrides or grant the entire host.
        paths = [*libraries(self.e.home), Path(target['prefix']).parent, Path(target['root'])]
        return sorted({str(path.resolve()) for path in paths})

    def _copy_snapshot(self, prefix, record, progress, event):
        dest = safe_target(prefix.parent, '.deck-fusion-runtime-backups/' + record['id'])
        dest.mkdir(parents=True, exist_ok=False)
        record['snapshot'] = str(dest / 'pfx')
        self._save(record)
        before = prefix_inventory(prefix, hashes=True, event=event)
        progress('Backing up the selected Proton prefix; links are preserved, not followed', .08)
        def checked_copy(src, dst):
            cancelled(event)
            if not stat.S_ISREG(os.lstat(src).st_mode): raise FusionError('Prefix changed while taking its snapshot. No installer was run.')
            return shutil.copy2(src, dst, follow_symlinks=False)
        shutil.copytree(prefix, dest / 'pfx', symlinks=True, copy_function=checked_copy)
        after = prefix_inventory(prefix, hashes=True, event=event)
        backup = prefix_inventory(dest / 'pfx', hashes=True, event=event)
        if before != after or content_index(before) != content_index(backup):
            raise FusionError('Prefix changed while taking its snapshot. No installer was run; retry after all prefix processes are closed.')
        atomic_json(dest / 'index.json', content_index(backup))
        record['snapshot_ready'] = True; self._save(record)

    def command(self, target, helper, verbs, force=False):
        prefix = Path(target['prefix'])
        env = self.environment()
        env['STEAM_COMPAT_DATA_PATH'] = str(prefix.parent)
        roots = steam_roots(self.e.home)
        if len(roots) != 1: raise FusionError('Multiple Steam installations detected. The active Steam installation cannot be chosen safely by this runtime workflow.')
        env['STEAM_DIR'] = str(roots[0])
        # The one shell string is code generated here, never caller-supplied.
        # Check Protontricks' resolved WINEPREFIX before Winetricks can mutate it.
        if force: raise FusionError('Unsafe Winetricks force mode is not supported.')
        flags = ['-q']
        executable = helper.get('winetricks', 'winetricks')
        runner = [executable]
        if 'vcrun2022' in verbs:
            script = self.e.source / 'vendor/winetricks/winetricks'
            if not script.is_file() or script.is_symlink() or sha256(script) != WINETRICKS_SHA256:
                raise FusionError('The bundled Winetricks recipe failed its integrity check. Reinstall the complete Deck Fusion ZIP.')
            runner = ['sh', str(script)]
        guarded = ('test "$(realpath -- "$WINEPREFIX")" = ' + shlex.quote(str(prefix)) +
                   ' || { printf "%s\\n" "Deck Fusion: wrong resolved WINEPREFIX; aborted" >&2; exit 73; }; '
                   'printf "DF_PREFIX=%s\\nDF_PROTON=%s\\n" "$WINEPREFIX" "$PROTON_PATH"; exec ' +
                   shlex.join([*runner, *flags, *verbs]))
        if helper['kind'] == 'flatpak':
            cmd = [helper['executable'], 'run',
                *['--filesystem=' + path for path in self.filesystem_grants(target)],
                *(['--filesystem=' + str(self.e.source / 'vendor/winetricks') + ':ro'] if 'vcrun2022' in verbs else []),
                '--env=STEAM_COMPAT_DATA_PATH=' + str(prefix.parent), '--env=STEAM_DIR=' + str(roots[0]),
                '--env=WINETRICKS_GUI=none', APP]
        else: cmd = [helper['executable']]
        return cmd + ['--no-background-wineserver', '-c', guarded, target['appid']], env

    def execute(self, command, env, log, progress, event=None, timeout=1800):
        """Stream bounded output. Terminate only this child process group on cancel."""
        log.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic(); stored = log.stat().st_size if log.exists() else 0
        tail = b''
        with log.open('ab') as out:
            header = ('\n$ ' + shlex.join(command) + '\n').encode(); out.write(header); out.flush()
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, env=env, start_new_session=True, bufsize=0)
            selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
            last = start
            try:
                while selector.get_map():
                    cancelled(event)
                    if time.monotonic() - start > timeout:
                        raise FusionError('Installer timed out. The prefix snapshot is retained. Review the log; a Windows dialog may require Desktop Mode.')
                    for key, _ in selector.select(.25):
                        chunk = os.read(key.fileobj.fileno(), 8192)
                        if not chunk: selector.unregister(key.fileobj); continue
                        tail = (tail + chunk)[-16000:]
                        if stored < MAX_LOG:
                            data = chunk[:MAX_LOG-stored]; out.write(data); out.flush(); stored += len(data)
                        lines = chunk.decode('utf-8', 'replace').strip().splitlines()
                        if lines:
                            text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', lines[-1])
                            progress(text[-220:], .55)
                    if time.monotonic() - last > 3:
                        progress(f'Installer still running ({int(time.monotonic()-start)} seconds). Do not launch the game.', .55)
                        last = time.monotonic()
                code = process.wait(timeout=10)
                if stored >= MAX_LOG:
                    out.write(b'\n[Output limit reached. Final installer output follows.]\n' + tail)
                out.write(f'\nExit status: {code}\n'.encode())
                out.flush()
                if code: raise FusionError(installer_error(code, tail.decode('utf-8', 'replace'), log))
            except BaseException:
                if process.poll() is None:
                    try: os.killpg(process.pid, signal.SIGTERM); process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        try: os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
                        except (ProcessLookupError, subprocess.TimeoutExpired): pass
                raise
            finally:
                selector.close(); process.stdout.close()

    def install(self, payload, progress, event=None):
        plan = self._plan(payload)
        if payload.get('approval') != plan['approval']:
            raise FusionError('The runtime target or prefix changed since confirmation. Refresh and confirm again; nothing was installed.')
        target = plan['target']; prefix = Path(target['prefix'])
        with self.maintenance_lock(target['appid']):
            self.idle(target); cancelled(event)
            if fingerprint(prefix_inventory(prefix)) != plan['inventory']:
                raise FusionError('The approved prefix changed before maintenance started. No installer was run.')
            identifier = uuid.uuid4().hex
            record = {'id': identifier, 'appid': target['appid'], 'prefix': str(prefix), 'started': time.time(),
                      'state': 'backing-up', 'snapshot_ready': False, 'runtimes': plan['runtimes'], 'force_vc': plan['force_vc']}
            self._save(record)
            log = self.e.store(target['appid']) / 'runtime-jobs' / identifier / 'installer.log'
            record['log'] = str(log)
            try:
                self._copy_snapshot(prefix, record, progress, event)
                self.idle(target); cancelled(event)
                if fingerprint(prefix_inventory(prefix)) != plan['inventory']:
                    raise FusionError('The approved prefix changed while preparing its snapshot. No installer was run.')
                record['state'] = 'installing'; self._save(record)
                # Each fixed verb has its own exit status. No --force/checksum bypass.
                for verb in plan['runtimes']:
                    before = self.evidence(str(prefix), pe_info(Path(target['exe']))['bits'])
                    if any(x['name'] == verb and x.get('satisfied') for x in before):
                        progress(f'{verb}: compatible runtime already installed; skipping', .6)
                        continue
                    cmd, env = self.command(target, plan['helper'], [verb], plan['force_vc'] and verb == 'vcrun2022')
                    self.execute(cmd, env, log, progress, event)
                record['evidence'] = self.evidence(str(prefix), pe_info(Path(target['exe']))['bits'])
                receipt_ok = all(x.get('satisfied', x['recorded']) for x in record['evidence'] if x['name'] in plan['runtimes'])
                record['state'] = 'completed' if receipt_ok else 'completed-unverified'
                record['note'] = ('Selected runtimes passed installation evidence checks. This does not prove that the game or mods launch.' if receipt_ok else
                    'The installer returned success, but the runtime DLLs and registered versions could not be verified. A stale Winetricks receipt may have skipped installation. Inspect the log; game/mod loading is unverified.')
                progress(record['note'], 1)
            except Exception as error:
                record.update(state='failed', error=str(error)); raise
            finally:
                record['finished'] = time.time(); self._save(record)
            return record

    def restore(self, payload, progress, event=None):
        plan = self._plan(payload, restoring=True)
        if payload.get('approval') != plan['approval']: raise FusionError('The restore target changed. Review the snapshot again.')
        target = plan['target']; prefix = Path(target['prefix'])
        record = self.snapshot_record(target) or {}
        snapshot, expected = self.snapshot_manifest(target, record)
        if fingerprint(expected) != plan['snapshot_index'] or content_index(prefix_inventory(snapshot, hashes=True, event=event)) != expected:
            raise FusionError('The saved prefix snapshot failed its integrity check. Nothing was restored.')
        with self.maintenance_lock(target['appid']):
            self.idle(target); cancelled(event)
            stage = prefix.parent / ('.df-before-restore-' + uuid.uuid4().hex)
            swapped = False
            progress('Preparing a verified copy of the saved prefix. The current prefix will be retained.', .15)
            def checked_copy(src, dst):
                cancelled(event)
                return shutil.copy2(src, dst, follow_symlinks=False)
            try:
                shutil.copytree(snapshot, stage, symlinks=True, copy_function=checked_copy)
                if content_index(prefix_inventory(stage, hashes=True, event=event)) != expected:
                    raise FusionError('The staged restore did not match the saved snapshot.')
                self.idle(target); cancelled(event)
                if fingerprint(prefix_inventory(prefix)) != plan['inventory']:
                    raise FusionError('The current prefix changed during restore preparation. Nothing was replaced.')
                # Atomic Linux exchange: never leave pfx absent between renames.
                record.update(state='restoring', displaced_prefix=str(stage))
                self._save(record)
                self.exchange(prefix, stage)
                swapped = True
                record.update(state='restored', restored=time.time(), displaced_prefix=str(stage))
                self._save(record)
                progress('Prefix snapshot restored. The replaced prefix is retained separately.', 1)
                return record
            finally:
                # Once exchanged, stage contains the user's former prefix. NEVER
                # delete it, even when recording the result fails afterwards.
                if not swapped and stage.exists(): shutil.rmtree(stage)

    def exchange(self, prefix, stage):
        libc = ctypes.CDLL(None, use_errno=True)
        function = getattr(libc, 'renameat2', None)
        if function is None: raise FusionError('Atomic directory exchange is unavailable. Prefix restore was not attempted; both copies remain available.')
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        if function(-100, os.fsencode(prefix), -100, os.fsencode(stage), 2) != 0:
            error = ctypes.get_errno()
            raise FusionError('The prefix filesystem does not permit atomic restore: ' + os.strerror(error) + '. The current prefix was not replaced.')

    def helper_plan(self):
        self.user_check()
        helper = self.helper()
        if helper['available']: raise FusionError('Protontricks is already available. No helper installation is needed.')
        flatpak = helper.get('flatpak')
        if not flatpak: raise FusionError('Flatpak is not installed. This plugin will not change SteamOS system packages.')
        code, remotes = self._probe([flatpak, 'remotes', '--user', '--columns=name,url'])
        if code: raise FusionError('Could not inspect user Flatpak remotes: ' + remotes)
        exists = False
        for line in remotes.splitlines():
            fields = line.split()
            if fields and fields[0] == 'flathub':
                exists = True
                if len(fields) < 2 or fields[1].rstrip('/') not in ('https://dl.flathub.org/repo', 'https://dl.flathub.org/repo/subset/floss'):
                    raise FusionError('The user remote named flathub does not have the expected official HTTPS URL. No package was downloaded.')
        commands = []
        if not exists:
            commands.append([flatpak, 'remote-add', '--user', '--if-not-exists', 'flathub', 'https://dl.flathub.org/repo/flathub.flatpakrepo'])
        commands.append([flatpak, 'install', '--user', '--noninteractive', '--assumeyes', 'flathub', APP])
        plan = {'commands': commands, 'note': 'Installs the official Protontricks Flatpak and dependencies for this user. Adds the official Flathub user remote if missing. Download size is chosen by Flatpak and may be substantial. No game prefix is changed.'}
        plan['approval'] = fingerprint(plan)
        return plan

    def install_helper(self, payload, progress, event=None):
        plan = self.helper_plan()
        if payload.get('approval') != plan['approval']: raise FusionError('Flatpak helper state changed. Review installation again.')
        log = self.e.data / 'protontricks-helper.log'
        for cmd in plan['commands']: self.execute(cmd, self.environment(), log, progress, event)
        helper = self.helper()
        if not helper['available']: raise FusionError(f'The helper was not detected after installation. Review {log}.')
        return {'helper': helper, 'log': str(log)}
