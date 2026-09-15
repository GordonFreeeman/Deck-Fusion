"""Create the Decky ZIP and verify its CRC, paths and runtime source integrity."""
from pathlib import Path
import hashlib,json,stat,zipfile
ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'package.json').read_text())['displayVersion']
output=ROOT.parent/f'Deck-Fusion-v{version}.zip'
files=[]
for f in sorted(ROOT.rglob('*')):
    rel=f.relative_to(ROOT)
    if not f.is_file() or f.is_symlink() or any(x in ('__pycache__','.pytest_cache','.git','.venv','venv','node_modules') for x in rel.parts):continue
    if f.suffix in ('.pyc','.pyo','.ttf','.otf','.woff','.woff2'):continue
    files.append(f)
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:z.write(f,str(Path('deck-fusion')/f.relative_to(ROOT)))
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    for i in z.infolist():
        assert i.filename.startswith('deck-fusion/') and '..' not in Path(i.filename).parts
        assert not stat.S_ISLNK(i.external_attr>>16)
    manifest=json.loads(z.read('deck-fusion/evidence/reviewed-code-sha256.json'))
    for path,digest in manifest.items():assert hashlib.sha256(z.read('deck-fusion/'+path)).hexdigest()==digest
    source=z.read('deck-fusion/src/index.js').decode('utf-8')
    studio=z.read('deck-fusion/src/studio.js').decode('utf-8')+'\n'+z.read('deck-fusion/src/setup.js').decode('utf-8')
    expected=source.replace('function Manager({startWizard=false}={}){',studio+'\nfunction Manager({startWizard=false}={}){')
    assert expected.encode('utf-8')==z.read('deck-fusion/dist/index.js')
    assert not json.loads(z.read('deck-fusion/plugin.json'))['flags']
sha=hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix('.zip.sha256').write_text(f'{sha}  {output.name}\n')
print(json.dumps({'archive':str(output),'bytes':output.stat().st_size,'entries':len(files),'sha256':sha},indent=2))
