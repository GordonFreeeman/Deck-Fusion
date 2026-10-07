"""Conservative, reversible graphics removal. Never accepts arbitrary removal paths."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import uuid
from collections import Counter
from fusion_identity import identify
from fusion_launch import shell_tokens, override_name, strip_wrapper, parse_dll_overrides
from fusion_transaction import Transaction
from fusion_util import FusionError, read_json, safe_target, sha256
from fusion_wine import inspect_overrides, module_basename

CANDIDATES = frozenset(('dxgi.dll','d3d9.dll','d3d10.dll','d3d11.dll','d3d12.dll','opengl32.dll',
 'version.dll','winmm.dll','winhttp.dll','wininet.dll','dbghelp.dll','dinput8.dll','dsound.dll','xinput1_3.dll','xinput9_1_0.dll',
 'optiscaler.dll','reshade.dll','reshade32.dll','reshade64.dll'))
PROFILE_FILES = ('manifest.json','profile.json','runtime.json','removal-last.json')


def encoded(obj): return (json.dumps(obj,indent=2,ensure_ascii=False)+'\n').encode()
def digest(obj): return hashlib.sha256(encoded(obj)).hexdigest()
def file_hash(path):
    if path.exists() and not path.is_file(): raise FusionError('Not a regular file: '+str(path))
    return sha256(path) if path.is_file() else None


def remove_overrides(text, names):
    """Edit only literal overrides for identified loaders that will be absent."""
    if not names: return text
    replacements=[]
    for raw,start,end in shell_tokens(text):
        value=shlex.split(raw)[0]
        if value.casefold()=='%command%': break
        key,sep,content=value.partition('=')
        if key not in ('WINEDLLOVERRIDES','WINEDLLOVERIDES') or not sep: continue
        groups=[]; changed=False
        if any(c in content for c in '$`'): raise FusionError('Expanded Wine overrides cannot be safely edited during removal.')
        for group in content.split(';'):
            modules,eq,order=group.partition('=')
            if not eq:
                if group: groups.append(group)
                continue
            keep=[n for n in modules.split(',') if override_name(n).lstrip('*') not in names]
            changed |= len(keep)!=len(modules.split(','))
            if keep: groups.append(','.join(keep)+'='+order)
        if changed: replacements.append((start,end,key+'='+shlex.quote(';'.join(groups)) if groups else ''))
    if replacements:
        lex=shlex.shlex(text,posix=True,punctuation_chars=';&|<>');lex.whitespace_split=True;lex.commenters=''
        if any(t and all(c in ';&|<>' for c in t) for t in lex) or '$(' in text or '`' in text:
            raise FusionError('Compound launch commands need manual editing before safe removal.')
    for start,end,value in reversed(replacements): text=text[:start]+value+text[end:]
    # Keep every unrelated token and its quoting; only trim removed edge assignments.
    return text.strip()


class GraphicsRemoval:
    def __init__(self, engine): self.e=engine

    def target(self, payload):
        appid=str(payload.get('appid') or payload.get('profile',{}).get('appid') or '')
        game=self.e.game(appid);root=Path(game['root']).resolve();store=self.e.store(appid)
        p=self.e.profile(appid)
        chosen=payload.get('exe') or payload.get('profile',{}).get('exe') or p.get('exe')
        if not chosen: raise FusionError('Choose the game executable before removing its graphics setup.')
        exe=Path(chosen)
        if not exe.is_absolute(): exe=root/exe
        try: exe=safe_target(root,str(exe.relative_to(root)))
        except ValueError: raise FusionError('The executable must be inside the selected game.')
        if not exe.is_file(): raise FusionError('Choose an existing game executable before removal.')
        p.update(root=str(root),exe=str(exe),appid=appid)
        return root,store,p

    def idle(self, p):
        safe=copy.deepcopy(p);safe['opti']['enabled']=False;safe['lsfg']['enabled']=False
        safe['reshade']['mode']='off';safe['wine']['custom_overrides']=''
        self.e.safety(safe)

    def known(self):
        known={};status=self.e.packages.status()
        for component,label in (('opti','OptiScaler'),('reshade','ReShade')):
            pkg=status.get(component,{})
            try:
                base=Path(pkg['path']);payload=pkg['payload']
                paths=[safe_target(base,payload['directory']+'/'+payload['dll'])] if component=='opti' else [safe_target(base,n) for n in payload['binaries'].values()]
                for p in paths:
                    if p.is_file(): known[sha256(p)]=label
            except (KeyError,TypeError,OSError,FusionError): continue
        return known

    def scan(self, root, tracked):
        found=set(tracked);notes=[];count=0
        def onerror(e): notes.append('Scan could not read '+str(e.filename)+'. Uninspected files are kept.')
        for directory,dirs,files in os.walk(root,followlinks=False,onerror=onerror):
            parent=Path(directory)
            dirs[:]=[d for d in dirs if not (parent/d).is_symlink() and d.casefold() not in ('.git','node_modules','reshade-shaders','deck-fusion-shaders')]
            if len(parent.relative_to(root).parts)>=10:
                if dirs: notes.append('Deep subfolders were not scanned; their untracked files are kept.')
                dirs[:]=[]
            for name in files:
                count+=1
                if name.casefold() in CANDIDATES: found.add((parent/name).relative_to(root).as_posix())
                if count>=150000: break
            if count>=150000:
                notes.append('Scan stopped at 150,000 files. Uninspected files are kept.');break
        return sorted(found),list(dict.fromkeys(notes))

    def status(self, payload):
        """Read-only discovery, independent of launch text or prefix load orders.

        Show removal only for an identifiable injector DLL. Unknown proxy names
        and leftover presets alone are not evidence of a graphics installation.
        """
        root,store,p=self.target(payload);tx=Transaction(root,store);old=tx.manifest()
        if old.get('root') and old['root']!=str(root):
            raise FusionError('The installation record belongs to another game folder.')
        tracked=old.get('files',{})
        if not isinstance(tracked,dict): raise FusionError('Invalid managed-file record.')
        names,notes=self.scan(root,tracked);known=self.known();counts=Counter(n.casefold() for n in names)
        found=[]
        for rel in names:
            if Path(rel).name.casefold() not in CANDIDATES or counts[rel.casefold()]>1:continue
            try:
                target=safe_target(root,rel);current=file_hash(target)
                if not current:continue
                meta=tracked.get(rel)
                if (meta and current==meta.get('installed')) or identify(target,known)[0]:found.append(rel)
            except (FusionError,OSError):continue # Unsafe/unknown files stay protected.
        last=read_json(safe_target(store,'removal-last.json'),None)
        return {'appid':p['appid'],'exe':p['exe'],'has_installation':bool(found),'files':found,
                'undo_available':bool(last and last.get('root')==str(root) and str(last.get('appid'))==p['appid']),
                'pending':bool(tx.pending()),'warnings':notes}

    def _plan(self, payload):
        root,store,p=self.target(payload);tx=Transaction(root,store)
        launch=payload.get('launch')
        if not isinstance(launch,str) or len(launch)>32768: raise FusionError('Read current Steam launch options before removal.')
        if tx.pending(): raise FusionError('An unfinished file operation must be recovered before removal or Undo.')
        if payload.get('undo'): return self._undo(payload,root,store,p,tx)
        old=tx.manifest();tracked=old.get('files',{})
        if old.get('root') and old['root']!=str(root): raise FusionError('The installation record belongs to another game folder.')
        if not isinstance(tracked,dict): raise FusionError('Invalid managed-file record.')
        names,notes=self.scan(root,tracked);known=self.known();counts=Counter(n.casefold() for n in names)
        rows=[];state={};changes={};absent=set();retained=set();sources={};modes={}
        for rel in names:
            meta=tracked.get(rel);target=root/rel
            try:
                target=safe_target(root,rel);current=file_hash(target);state[rel]=current
                if counts[rel.casefold()]>1: raise FusionError('Ambiguous filename casing; keep both files')
            except (FusionError,OSError) as error:
                rows.append({'path':rel,'action':'keep','reason':str(error),'identity':'Unidentified'})
                state[rel]='protected';retained.add(target.stem.casefold());continue
            label,reason=(identify(target,known) if current and target.suffix.casefold()=='.dll' and target.name.casefold() in CANDIDATES else (None,None))
            if meta and current==meta.get('installed'):
                backup=tx._original(meta['before'],rel) if meta.get('before') else None
                # Do not reactivate a positively identified older injector that was replaced during Apply.
                if backup and target.name.casefold() in CANDIDATES and identify(backup,known)[0]:
                    notes.append('The previous injector backup for '+rel+' stays archived.');backup=None
                changes[rel]=backup
                if backup: sources[rel]=sha256(backup);modes['game/'+rel]=meta.get('mode',0o644)
                else: absent.add(target.stem.casefold())
                rows.append({'path':rel,'action':'restore-original' if backup else 'back-up-and-remove','identity':label or 'Deck Fusion file','reason':'Matches the recorded installation hash'})
            elif meta and current is None and meta.get('before'):
                backup=tx._original(meta['before'],rel)
                if target.name.casefold() in CANDIDATES and identify(backup,known)[0]:
                    rows.append({'path':rel,'action':'keep','identity':'Archived injector','reason':'File is already absent; previous injector stays archived'})
                else:
                    changes[rel]=backup;sources[rel]=sha256(backup);modes['game/'+rel]=meta.get('mode',0o644)
                    rows.append({'path':rel,'action':'restore-original','identity':'Original backup','reason':'Managed target is missing; original backup verified'})
            elif label and current:
                changes[rel]=None;absent.add(target.stem.casefold())
                rows.append({'path':rel,'action':'back-up-and-remove','identity':label,'reason':reason})
            else:
                retained.add(target.stem.casefold())
                rows.append({'path':rel,'action':'keep','identity':'Changed managed file' if meta else 'Unidentified','reason':'Already absent' if current is None else 'Ownership cannot be established; file stays untouched'})
        # Only DLL overrides for absent loaders are edited, never shared SDK dependencies.
        removed={Path(rel).stem.casefold() for rel,src in changes.items() if src is None and Path(rel).name.casefold() in CANDIDATES}-retained
        after=remove_overrides(launch,removed)
        saved=copy.deepcopy(p);saved['opti']['enabled']=False;saved['opti']['fg']=False;saved['reshade']['mode']='off'
        custom=parse_dll_overrides(saved['wine']['custom_overrides'],strict=True)
        saved['wine']['custom_overrides']=';'.join(k+'='+v for k,v in custom.items() if override_name(k).lstrip('*') not in removed)
        runtime=read_json(safe_target(store,'runtime.json'),{})
        has_runtime=bool(runtime)
        runtime.update(opti_enabled=False,enable_nvapi=False,fsr4_watermark=False,dll_overrides={})
        runtime.pop('bg3_target',None)
        runtime['custom_dll_overrides']=parse_dll_overrides(saved['wine']['custom_overrides'],strict=True)
        keep_wrapper=has_runtime and (runtime.get('lsfg',{}).get('enabled') or runtime.get('base_fps') or runtime['custom_dll_overrides'])
        if not keep_wrapper: after=strip_wrapper(after,self.e.wrapper,p['appid']).strip()
        if removed:
            context=inspect_overrides(self.e,p,launch)
            uncertain=list(dict.fromkeys(x for x in context.get('warnings',[]) if any(v in x for v in ('not inspected','not fully inspected','Cannot completely inspect'))))
            if uncertain:raise FusionError('Cannot verify prefix overrides before removal: '+' '.join(uncertain))
            for item in context['registry']:
                if module_basename(item['name']) in removed and item['order']=='n':
                    raise FusionError('The Proton prefix forces native-only loading for '+item['name']+'. Change that override to native,builtin before removing its DLL; no prefix setting was changed.')
        new_manifest={'root':str(root),'files':{},'original_launch':old.get('original_launch') if keep_wrapper else None,'installed_launch':after}
        extras={'profile.json':encoded(saved),'runtime.json':encoded(runtime),'manifest.json':encoded(new_manifest)}
        before_profile={rel:file_hash(safe_target(store,rel)) for rel in PROFILE_FILES}
        notes += ['Unknown DLLs, edited files, untracked presets/shader folders and shared SDK DLLs stay in place.',
                  'Every changed file is backed up. Undo refuses to overwrite files changed after removal.',
                  'LSFG settings, frame caps, Windows runtimes and unrelated launch arguments are retained. Unapplied draft edits are discarded after removal.']
        last=read_json(safe_target(store,'removal-last.json'),None)
        meaningful=bool(changes or saved['opti']!=p['opti'] or saved['reshade']!=p['reshade'] or after!=launch)
        result={'appid':p['appid'],'root':str(root),'exe':p['exe'],'files':rows,'warnings':notes,
                'launch_before':launch,'launch_after':after,'undo_available':bool(last),
                'file_count':len(changes),'can_apply':meaningful,'undo':False,
                'state':{'game':state,'profile':before_profile},'originals':sources,'modes':modes}
        result['approval_token']=digest(result)
        return result,changes,extras,p

    def _undo(self,payload,root,store,p,tx):
        last=read_json(safe_target(store,'removal-last.json'),None)
        token=last.get('token','') if isinstance(last,dict) else ''
        if not re.fullmatch('[0-9a-f]{32}',token) or last.get('root')!=str(root) or last.get('appid')!=p['appid']:
            raise FusionError('No matching removal backup is available for this game.')
        work=safe_target(store,'transactions/'+token)
        receipt=read_json(safe_target(work,'receipt.json'),{})
        if receipt.get('phase')!='committed' or receipt.get('operation')!='remove-graphics' or receipt.get('root')!=str(root) or receipt.get('token')!=token:
            raise FusionError('Removal backup record is missing or invalid.')
        if payload['launch']!=receipt.get('launch_after'):
            raise FusionError('Steam launch options changed after removal. Undo stopped to preserve your edits.')
        game={};extras={};state={'game':{},'profile':{}};rows=[];modes={};backups={}
        for a in receipt['actions']:
            area=a.get('area');rel=a.get('path')
            if area not in ('game','profile') or (area=='profile' and rel not in PROFILE_FILES):raise FusionError('Invalid removal backup path.')
            target=safe_target(root if area=='game' else store,rel);current=file_hash(target)
            if current!=a['after_hash']: raise FusionError('File changed after removal; Undo will not overwrite it: '+rel)
            state[area][rel]=current
            source=safe_target(work,a['before']) if a.get('before') else None
            if source and (not source.is_file() or sha256(source)!=a['before_hash']): raise FusionError('Removal backup is damaged: '+rel)
            (game if area=='game' else extras)[rel]=source
            backups[area+'/'+rel]=a['before_hash'];modes[area+'/'+rel]=a['before_mode']
            if area=='game':rows.append({'path':rel,'action':'undo-removal','identity':'Removal backup','reason':'Current file and backup hashes verified'})
        result={'appid':p['appid'],'root':str(root),'exe':p['exe'],'files':rows,
                'warnings':['Undo restores the files, saved settings and Steam launch options from immediately before removal.'],
                'launch_before':payload['launch'],'launch_after':receipt['launch_before'],'undo':True,'undo_available':True,
                'file_count':len(game),'can_apply':True,'state':state,'originals':backups,'modes':modes,'undo_token':token}
        result['approval_token']=digest(result)
        return result,game,extras,p

    def plan(self,payload):
        result,*_=self._plan(payload)
        try:self.idle(self.target(payload)[2]);result['blockers']=[]
        except FusionError as e:result['blockers']=[str(e)]
        return result

    def prepare(self,payload,progress=lambda *_:None):
        result,game,extras,p=self._plan(payload)
        if not result['can_apply']:raise FusionError('No identified graphics installation needs removal.')
        if payload.get('approval')!=result['approval_token']:raise FusionError('Files or settings changed after removal review. Scan again; nothing was removed.')
        self.idle(p)
        token=uuid.uuid4().hex;store=self.e.store(p['appid']);tx=Transaction(Path(p['root']),store)
        if not result['undo']:extras['removal-last.json']=encoded({'token':token,'root':p['root'],'appid':p['appid']})
        expected={area:{k:result['state'][area][k] for k in data} for area,data in [('game',game),('profile',extras)]}
        modes={(key.split('/',1)[0],key.split('/',1)[1]):value for key,value in result.get('modes',{}).items()}
        def guard():
            self.idle(p)
            fresh,*_=self._plan(payload)
            if fresh['approval_token']!=result['approval_token']:raise FusionError('The removal review changed during backup. No game files were changed.')
        return tx.prepare_patch(game,extras,expected,result['launch_before'],result['launch_after'],token,
                                'undo-graphics-removal' if result['undo'] else 'remove-graphics',guard,progress,modes)
