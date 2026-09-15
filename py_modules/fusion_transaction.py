"""Journaled, two-phase game-file installation. Never recursively deletes a game directory."""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import stat
import uuid
from pathlib import Path
from fusion_util import FusionError, atomic_bytes, atomic_json, read_json, safe_target, sha256


def source_hash(source: Path | bytes) -> str:
    return sha256(source) if isinstance(source, Path) else hashlib.sha256(source).hexdigest()


def copy_atomic(source: Path | bytes, target: Path, mode: int = 0o644) -> None:
    if isinstance(source, bytes):
        atomic_bytes(target, source, mode); return
    if target.is_symlink(): raise FusionError(f'Refusing symlink target: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name('.' + target.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with source.open('rb') as src, tmp.open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
            dst.flush(); os.fsync(dst.fileno())
        os.chmod(tmp, mode); os.replace(tmp, target)
    finally: tmp.unlink(missing_ok=True)


class ManagedFilesChanged(FusionError):
    """A reviewable drift condition, not permission to skip other safety checks."""
    def __init__(self, repairs):
        self.repairs = repairs
        paths = ', '.join(item['path'] for item in repairs[:12])
        super().__init__('Managed files were deleted or changed outside Deck Fusion: ' + paths +
                         '. Use Force apply settings to reinstall this configuration from a reviewed plan.')


class Transaction:
    def __init__(self, root: Path, store: Path):
        self.root, self.store = root.resolve(), store.resolve()
        self.store.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store / 'manifest.json'
        self.journal_path = self.store / 'pending.json'

    def manifest(self):
        return read_json(self.manifest_path, {'files': {}, 'original_launch': None, 'installed_launch': None})

    def pending(self): return read_json(self.journal_path, None)

    def inspect(self, desired: dict[str, Path | bytes], consent: bool = False,
                force_repair: bool = False) -> dict:
        if not isinstance(force_repair, bool):
            raise FusionError('Force repair must be true or false.')
        old = self.manifest()
        manifest_hash = sha256(self.manifest_path) if self.manifest_path.is_file() else None
        if old.get('root') and old['root'] != str(self.root):
            raise FusionError('This profile belongs to another game folder. Restore it before selecting a different installation.')
        changes, conflicts, modified, repairs = [], [], [], []
        file_state = {}
        folded = set()
        for rel in sorted(set(desired) | set(old['files'])):
            if rel.casefold() in folded: raise FusionError(f'Case-insensitive filename collision: {rel}')
            folded.add(rel.casefold())
            p = safe_target(self.root, rel)
            if p.exists() and not p.is_file(): raise FusionError(f'Target is not a regular file: {rel}')
            # Wine may load differently-cased names; never install a shadow copy alongside one.
            if p.parent.exists():
                matches = [x for x in p.parent.iterdir() if x.name.casefold() == p.name.casefold() and x.name != p.name]
                if matches: raise FusionError(f'Filename casing conflict: {matches[0].name} versus {p.name}. Resolve it before installation.')
            cur = sha256(p) if p.exists() else None
            meta = old['files'].get(rel)
            newhash = source_hash(desired[rel]) if rel in desired else (meta.get('before') if meta else None)
            drift = bool(meta and cur != meta['installed'])
            editable = p.suffix.lower() in ('.ini', '.txt', '.json', '.toml')
            if meta and meta.get('before') and (force_repair or rel not in desired):
                self._original(meta['before'], rel)  # Force never excuses a damaged original backup.
            if drift:
                action = ('reinstall' if cur is None else 'back-up-and-replace') if rel in desired else (
                    ('restore-original' if meta.get('before') else 'leave-absent') if cur is None else 'keep-and-untrack')
                item = {'path': rel, 'state': 'missing' if cur is None else 'modified', 'action': action}
                repairs.append(item)
                if not editable: modified.append(item)
            if not meta and cur is not None and cur != newhash:
                conflicts.append(rel)
            # An obsolete, independently changed file is not ours to delete/restore.
            # Adopt its actual on-disk state as an untracked file instead.
            preserve = force_repair and drift and rel not in desired and not (cur is None and meta.get('before'))
            if preserve:
                newhash = cur
            file_state[rel] = {'before': cur, 'after': newhash}
            if preserve:
                changes.append({'path': rel, 'action': 'leave-absent' if cur is None else 'keep-and-untrack'})
            elif rel not in desired:
                changes.append({'path': rel, 'action': 'restore' if meta.get('before') else 'remove'})
            elif cur != newhash:
                changes.append({'path': rel, 'action': 'replace' if cur is not None else 'add'})
        if modified and not force_repair:
            raise ManagedFilesChanged(modified)
        return {'file_state': file_state, 'manifest_hash': manifest_hash,
                'changes': changes, 'conflicts': conflicts, 'repairs': repairs if force_repair else [],
                'force_repair': force_repair,
                'needs_consent': bool((conflicts or (force_repair and repairs)) and not consent),
                'file_count': len(desired), 'bytes': sum(p.stat().st_size if isinstance(p, Path) else len(p) for p in desired.values())}

    def _original(self, digest, rel):
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise FusionError(f'Original backup reference is invalid: {rel}')
        backup = safe_target(self.store, 'originals/' + digest)
        if not backup.is_file() or sha256(backup) != digest:
            raise FusionError(f'Original backup is missing or damaged: {rel}')
        return backup

    def prepare(self, desired: dict[str, Path | bytes], extras: dict[str, bytes],
                original_launch: str, installed_launch: str, consent=False, progress=lambda *_: None, reset_origin=False, expected_state=None,
                force_repair=False, expected_manifest=None) -> dict:
        if self.pending(): raise FusionError('An interrupted operation needs recovery in the Apply tab first.')
        if force_repair and (not consent or expected_state is None):
            raise FusionError('Force repair requires approval of the displayed repair plan.')
        if force_repair and reset_origin:
            raise FusionError('Force repair cannot be used for Restore.')
        review = self.inspect(desired, consent, force_repair)
        if force_repair and review['manifest_hash'] != expected_manifest:
            raise FusionError('The managed-file record changed after confirmation. Review the repair again.')
        if expected_state is not None and review['file_state'] != expected_state:
            raise FusionError('Files changed after confirmation. Click Apply again to review the new state; nothing was installed.')
        if review['needs_consent']:
            raise FusionError('Existing files would be replaced. Review the conflict list and explicitly enable backing up existing mod files.')
        old = self.manifest(); token = uuid.uuid4().hex
        preserved = {item['path'] for item in review['repairs']
                     if item['action'] in ('keep-and-untrack', 'leave-absent')}
        work = self.store / 'transactions' / token
        work.mkdir(parents=True)
        orig = self.store / 'originals'; orig.mkdir(exist_ok=True)
        if shutil.disk_usage(self.root).free < review['bytes'] + 16 * 1024 * 1024:
            raise FusionError('Insufficient free space in the game library for an atomic installation.')
        new = {'root': str(self.root), 'files': {},
               'original_launch': old.get('original_launch') if old.get('original_launch') is not None else original_launch,
               'installed_launch': installed_launch}
        if reset_origin:
            new['original_launch'] = None
            new['installed_launch'] = None
        actions = []
        # Snapshot and stage EVERY file before the first game-file mutation.
        for rel in sorted(set(desired) | set(old['files'])):
            target = safe_target(self.root, rel); previous = old['files'].get(rel)
            mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
            original = previous.get('before') if previous else None
            if previous is None and target.exists():
                original = sha256(target)
                backup = orig / original
                if not backup.exists(): copy_atomic(target, backup, mode)
            if rel in desired:
                source = desired[rel]
                new['files'][rel] = {'installed': source_hash(source), 'before': original,
                                      'mode': previous.get('mode', mode) if previous else mode}
            elif rel in preserved:
                source = target if target.exists() else None
            else:
                source = self._original(original, rel) if original else None
                mode = previous.get('mode', mode)
            self._stage(actions, work, target, source, mode, 'game', rel)
            if rel in preserved: actions[-1]['skip_write'] = True
            if actions[-1]['before_hash'] != review['file_state'][rel]['before']:
                raise FusionError(f'File changed after approval: {rel}. Apply again to review the new state.')
            if actions[-1]['after_hash'] != review['file_state'][rel]['after']:
                raise FusionError(f'Component changed after approval: {rel}. Apply again to review the update.')
        for rel, data in extras.items():
            target = safe_target(self.store, rel)
            self._stage(actions, work, target, data, 0o600, 'profile', rel)
        self._stage(actions, work, self.manifest_path,
                    (__import__('json').dumps(new, indent=2) + '\n').encode(), 0o600, 'profile', 'manifest.json')
        if force_repair and (sha256(self.manifest_path) if self.manifest_path.is_file() else None) != review['manifest_hash']:
            raise FusionError('The managed-file record changed while staging. No game files were changed; review again.')
        journal = {'token': token, 'root': str(self.root), 'phase': 'applying', 'actions': actions,
                   'force_repair': force_repair, 'repairs': review['repairs'],
                   'launch_before': original_launch, 'launch_after': installed_launch}
        atomic_json(self.journal_path, journal)
        try:
            for i, action in enumerate(actions):
                self._apply(action, work)
                progress(f'Installing file {i + 1} / {len(actions)}', (i + 1) / max(1, len(actions)))
            journal['phase'] = 'awaiting-steam'
            atomic_json(self.journal_path, journal)
        except BaseException:
            # If rollback also fails, keep the journal for explicit recovery.
            self.rollback(token)
            raise
        return {'token': token, 'launch_before': original_launch, 'launch_after': installed_launch,
                'changes': review['changes'], 'force_repair': force_repair, 'repairs': review['repairs']}

    def _stage(self, actions, work, target, source, mode, area, rel):
        idx = str(len(actions)); before = None
        if target.exists():
            before = f'{idx}.before'; copy_atomic(target, work / before, 0o600)
        after = None
        if source is not None:
            after = f'{idx}.after'; copy_atomic(source, work / after, 0o600)
        actions.append({'area': area, 'path': rel, 'before': before, 'after': after, 'mode': mode,
                        'before_mode': stat.S_IMODE(target.stat().st_mode) if target.exists() else mode,
                        'before_hash': sha256(work / before) if before else None,
                        'after_hash': sha256(work / after) if after else None})

    def _target(self, action):
        return safe_target(self.root if action['area'] == 'game' else self.store, action['path'])

    def _apply(self, action, work):
        target = self._target(action)
        current = sha256(target) if target.exists() else None
        if current != action['before_hash']:
            raise FusionError(f'File changed during installation: {action["path"]}')
        if action.get('skip_write'): return
        if action['after']: copy_atomic(work / action['after'], target, action['mode'])
        else: target.unlink(missing_ok=True)

    def _journal(self, token):
        j = self.pending()
        if not j or j['token'] != token or j['root'] != str(self.root):
            raise FusionError('The recovery token is invalid or belongs to another installation.')
        return j, self.store / 'transactions' / token

    def finalize(self, token: str, launch_verified: str) -> dict:
        j, work = self._journal(token)
        if j['phase'] != 'awaiting-steam' or launch_verified != j['launch_after']:
            raise FusionError('Steam launch options were not verified. Installation remains recoverable.')
        for a in j['actions']:
            p = self._target(a)
            if (sha256(p) if p.exists() else None) != a['after_hash']:
                raise FusionError(f'Installed file changed before verification: {a["path"]}')
        # Keep snapshots on disk. They preserve edited INIs and aid manual disaster recovery.
        atomic_json(work / 'receipt.json', {**j, 'phase': 'committed'})
        self.journal_path.unlink()
        return {'committed': True, 'receipt': str(work / 'receipt.json'),
                'force_repair': j.get('force_repair', False), 'repairs': j.get('repairs', [])}

    def rollback(self, token: str) -> dict:
        j, work = self._journal(token)
        for a in reversed(j['actions']):
            target = self._target(a)
            now = sha256(target) if target.exists() else None
            if now == a['before_hash']: continue
            if now != a['after_hash']:
                raise FusionError(f'Recovery stopped because a file changed independently: {a["path"]}. Journal retained.')
            if a['before']:
                backup = work / a['before']
                if not backup.is_file() or sha256(backup) != a['before_hash']:
                    raise FusionError(f'Damaged recovery snapshot: {a["path"]}')
                copy_atomic(backup, target, a['before_mode'])
            else: target.unlink(missing_ok=True)
        atomic_json(work / 'receipt.json', {**j, 'phase': 'rolled-back'})
        self.journal_path.unlink()
        return {'rolled_back': True, 'launch_options': j['launch_before']}
