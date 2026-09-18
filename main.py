"""Decky backend. Standard library only. Runs without Decky's _root flag."""
from __future__ import annotations
import asyncio
import fcntl
import functools
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'py_modules'))
from fusion_engine import Engine
from fusion_util import FusionError, atomic_json

try:
    import decky_plugin
    LOG = decky_plugin.logger
except ImportError:
    decky_plugin = None
    LOG = logging.getLogger('deck-fusion')


def exposed(function):
    """Keep meaningful errors in the result, instead of Decky's generic PythonException."""
    @functools.wraps(function)
    async def wrapped(self, *args, **kwargs):
        try:
            return {'ok': True, 'result': await function(self, *args, **kwargs)}
        except Exception as error:
            identifier = uuid.uuid4().hex[:10]
            expected = isinstance(error, FusionError)
            message = str(error) if expected else f'{type(error).__name__}: {error}'
            details = {'id': identifier, 'code': 'configuration' if expected else 'backend',
                       'message': message or 'The backend operation failed.',
                       'method': function.__name__}
            LOG.error('Deck Fusion error %s in %s: %s\n%s', identifier, function.__name__, error, traceback.format_exc())
            try:
                if getattr(self, '_engine', None):
                    atomic_json(self._engine.data / 'last-error.json', {**details, 'time': int(time.time())})
            except Exception:
                LOG.exception('Could not persist error diagnostics')
            return {'ok': False, 'error': details}
    return wrapped


class Plugin:
    async def _main(self):
        self._initialize()
        LOG.info('Deck Fusion 0.3-beta6 initialized, no root privilege requested.')

    def _initialize(self):
        if getattr(self, '_engine', None) is not None: return
        home = getattr(decky_plugin, 'DECKY_USER_HOME', None) if decky_plugin else None
        home = home or os.environ.get('DECKY_USER_HOME') or str(Path.home())
        self._engine = Engine(Path(home), HERE)
        self._mutex = threading.RLock()
        self._jobs = {}
        self._tasks = set()
        self._runtime_cancels = {}
        self._closing = False

    def _call_sync(self, action: str, payload: dict, progress=lambda *_: None, cancel=None):
        e = self._engine
        # Inter-process lock also prevents a hot-reloaded backend racing its old instance.
        with self._mutex, (e.data / 'backend.lock').open('a+') as lock:
            try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise FusionError('Another Deck Fusion operation is finishing. Its recovery journal is preserved; retry after it completes.')
            try:
                appid = str(payload.get('appid', ''))
                if action == 'state':
                    e.packages.seed_bundled(progress)
                    return {'packages':e.packages.status(), 'games':e.games(), 'data':str(e.data),
                            'hardware':e.hardware(), 'settings':e.settings(), 'bundled':e.packages.bundle_status(),
                            'legacy_layers':e.old_layers(), 'lsfg_install':__import__('fusion_util').read_json(e.data/'lsfg-install.json',None)}
                if action == 'running_games': return __import__('fusion_steam').running_appids(e.games())
                if action == 'runtime_status': return e.prereqs.status(payload)
                if action == 'runtime_plan': return e.prereqs.plan(payload)
                if action == 'runtime_install': return e.prereqs.install(payload, progress, cancel)
                if action == 'runtime_restore': return e.prereqs.restore(payload, progress, cancel)
                if action == 'runtime_helper_plan': return e.prereqs.helper_plan()
                if action == 'runtime_helper_install': return e.prereqs.install_helper(payload, progress, cancel)
                if action == 'settings': return e.set_settings(payload)
                if action == 'https': return __import__('fusion_network').tls_context()[1]
                if action == 'check_updates': return e.packages.check_updates(progress)
                if action == 'bundled_setup': return e.packages.seed_bundled(progress, retry=True)
                if action == 'profile': return e.profile(appid)
                if action == 'scan': return e.scan(appid)
                if action == 'detect_api': return e.detect_api(payload['profile'], payload.get('launch', ''))
                if action == 'launch_cleanup': return e.launch_cleanup(appid, payload.get('launch', ''))
                if action == 'schema': return e.schema(appid)
                if action == 'wine_context': return e.wine_context(payload['profile'], payload.get('launch', ''))
                if action == 'diagnostics': return e.diagnostics(appid)
                if action == 'game_diagnostics': return e.game_diagnostics(appid, payload.get('exe'))
                if action == 'mod_diagnostics': return e.mod_diagnostics(appid, payload.get('exe'))
                if action == 'sync_from_disk': return e.sync_from_disk(appid)
                if action == 'install': return e.packages.install(payload['component'],progress,latest=bool(payload.get('latest')))
                if action == 'shader':
                    return e.packages.install_shader_pack(payload['id'],progress,payload.get('repository',''),payload.get('branch',''))
                if action == 'common_shaders':
                    result = []
                    for i, key in enumerate(('standard','sweetfx','fxshaders')):
                        result.append(e.packages.install_shader_pack(key,lambda text, fraction: progress(text,(i+fraction)/3)))
                    return result
                if action == 'lsfg_setup': return e.setup_lsfg(payload.get('dll',''))
                if action == 'legacy_disable': return e.disable_old_layers()
                if action == 'requirements': return e.requirements(payload['profile'])
                if action == 'plan': return e.plan(payload['profile'],payload['launch'],bool(payload.get('remove')),force_repair=payload.get('force_repair',False))
                if action == 'review':
                    if not isinstance(payload.get('profile'),dict) or not isinstance(payload.get('launch'),str):
                        raise FusionError('Review requires a selected game profile and the current launch options. Select a game, then Read current Steam launch options.')
                    return e.review(payload['profile'],payload['launch'],bool(payload.get('remove')),force_repair=payload.get('force_repair',False))
                if action == 'prepare' and payload.get('approval') is not None:
                    return e.prepare_approved(payload['profile'],payload['launch'],payload['approval'],bool(payload.get('remove')),progress,payload.get('launch_actual'),force_repair=payload.get('force_repair',False))
                if action == 'prepare': return e.prepare(payload['profile'],payload['launch'],bool(payload.get('remove')),progress,payload.get('launch_actual'),force_repair=payload.get('force_repair',False))
                if action == 'finish': return e.finish(appid,payload['token'],payload['verified'])
                if action == 'rollback': return e.rollback(appid,payload['token'])
                if action == 'hot_lsfg': return e.hot_lsfg(appid,payload['changes'])
                if action == 'import_preset':
                    f = Path(payload['path']).expanduser().resolve()
                    allowed = f.is_relative_to(e.home) or any(f.is_relative_to(Path(g['root'])) for g in e.games())
                    if not allowed or f.suffix.lower() != '.ini' or not f.is_file() or f.stat().st_size > 1024*1024:
                        raise FusionError('Choose a ReShade .ini preset under your home or a Steam library (maximum 1 MB).')
                    text = f.read_text('utf-8-sig'); ini = __import__('fusion_util').ini_read(text)
                    techniques = [x.strip() for x in ini.get('__ROOT__','Techniques',fallback='').split(',') if x.strip()]
                    uniforms = {s:dict(ini[s]) for s in ini.sections() if s.lower().endswith('.fx')}
                    return {'raw_preset':text,'techniques':techniques,'uniforms':uniforms}
                raise FusionError('Unknown plugin action.')
            finally: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)

    @exposed
    async def rpc(self, action: str, payload: dict):
        self._initialize()
        if self._closing: raise FusionError('Plugin is unloading.')
        if not isinstance(action,str) or not isinstance(payload,dict): raise FusionError('Invalid plugin request.')
        if len(json.dumps(payload)) > 3*1024*1024: raise FusionError('Request exceeds 3 MB.')
        return await asyncio.to_thread(self._call_sync,action,payload)

    @exposed
    async def start_job(self, action: str, payload: dict):
        self._initialize()
        if self._closing: raise FusionError('Plugin is unloading.')
        if action not in ('install','shader','common_shaders','lsfg_setup','legacy_disable','scan','prepare','review','plan','check_updates','bundled_setup','runtime_status','runtime_plan','runtime_install','runtime_restore','runtime_helper_plan','runtime_helper_install'):
            raise FusionError('Unsupported job.')
        if not isinstance(payload,dict) or len(json.dumps(payload)) > 3*1024*1024:
            raise FusionError('Invalid job payload.')
        if any(j['state']=='running' for j in self._jobs.values()):
            raise FusionError('An operation is already in progress. Its status remains visible in Tools.')
        job_id = uuid.uuid4().hex
        job = {'id':job_id,'action':action,'state':'running','message':'Starting','progress':0.,'started':time.time()}
        self._jobs[job_id] = job
        cancel = threading.Event() if action in ('runtime_install','runtime_restore','runtime_helper_install') else None
        if cancel: self._runtime_cancels[job_id] = cancel
        def progress(message, fraction): job.update(message=str(message),progress=max(0.,min(1.,float(fraction))))
        async def runner():
            try:
                result = await asyncio.to_thread(self._call_sync,action,payload,progress,cancel)
                job.update(state='done',progress=1.,message='Completed',result=result)
            except Exception as error:
                LOG.error('Deck Fusion %s failed: %s\n%s',action,error,traceback.format_exc())
                job.update(state='error',message=str(error),error=str(error))
            finally:
                job['finished'] = time.time()
                self._runtime_cancels.pop(job_id, None)
        task = asyncio.create_task(runner()); self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        # Bound memory without removing a running job or the most recent results.
        if len(self._jobs) > 24:
            for key in list(self._jobs)[:-16]:
                if self._jobs[key]['state'] != 'running': del self._jobs[key]
        return {'id':job_id}

    @exposed
    async def cancel_runtime(self, job_id: str):
        self._initialize()
        event = self._runtime_cancels.get(job_id)
        if event is None: raise FusionError('No cancellable runtime operation is active for this job.')
        event.set()
        return {'requested': True, 'note': 'Cancellation requested. Completed snapshots and any partial installer changes are retained; see the runtime receipt.'}

    @exposed
    async def get_job(self, job_id: str):
        self._initialize()
        if job_id not in self._jobs: raise FusionError('Job not found. Check Apply → recovery if the plugin was restarted.')
        return dict(self._jobs[job_id])

    @exposed
    async def active_jobs(self):
        self._initialize()
        return [dict(j) for j in self._jobs.values() if j['state']=='running']

    async def _unload(self):
        self._closing = True
        # Do not cancel a thread midway through a journaled write. Forced process termination
        # is handled by the persistent pending.json recovery flow on next load.
        if getattr(self,'_tasks',None): await asyncio.gather(*self._tasks,return_exceptions=True)

    async def _uninstall(self):
        # Game integration must be restored through the UI while Steam's API is available.
        # Persistent wrapper deliberately remains so removing the plugin cannot break launches.
        LOG.info('Plugin removed. Managed game backups and persistent launch wrapper retained.')
