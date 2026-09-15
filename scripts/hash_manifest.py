"""Record hashes of the current release sources after build and verification."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
paths = [root / name for name in (
    'main.py', 'package.json', 'package-lock.json', 'plugin.json', 'README.md',
    'CHANGELOG.md', 'LICENSE', 'requirements-dev.txt', 'dist/index.js')]
for directory, pattern in [('src', '*.js'), ('py_modules', '*.py'), ('scripts', '*.py')]:
    paths.extend((root / directory).glob(pattern))
paths.extend(path for path in (root / 'vendor').rglob('*') if path.is_file())
manifest = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths))}
(root / 'evidence').mkdir(exist_ok=True)
(root / 'evidence/reviewed-code-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'Recorded {len(manifest)} file hashes. This records integrity, not a review approval.')
