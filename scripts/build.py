"""Dependency-free build. Source is self-contained ES module using Decky's host UI."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / 'src/index.js').read_text('utf-8')
studio = (root / 'src/studio.js').read_text('utf-8') + '\n' + (root / 'src/setup.js').read_text('utf-8')
source = source.replace('function Manager({startWizard=false}={}){', studio + '\nfunction Manager({startWizard=false}={}){')
(root / 'dist').mkdir(exist_ok=True)
(root / 'dist/index.js').write_text(source, encoding='utf-8')
print('Built dist/index.js')
