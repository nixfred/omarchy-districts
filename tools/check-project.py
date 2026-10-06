#!/usr/bin/env python3
"""Check the standalone source tree without loading or installing the plugin."""
import ast
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'manifest.json').read_text())
assert manifest['id'] == 'nixfred.districts'
assert manifest['version'] == '2.2.0'
for entry in manifest['entryPoints'].values():
    assert (ROOT / entry).is_file(), f'Missing entry point: {entry}'

# Read the installer's release list without importing or running its code.
installer = ast.parse((ROOT / 'install.py').read_text())
runtime = next(ast.literal_eval(node.value) for node in installer.body
               if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'RUNTIME' for t in node.targets))
assert len(runtime) == 14
for name in runtime:
    path = ROOT / name
    assert path.is_file(), f'Missing release file: {name}'
    if path.parent.name == 'v2.2':
        assert path.read_bytes() == (ROOT / path.name).read_bytes(), f'Root/runtime drift: {name}'
    if path.suffix == '.py':
        ast.parse(path.read_text(), filename=name)
    if path.suffix in ('.qml', '.js', '.py'):
        assert not re.search(r'/home/[^/]+/|Documents/Codex|task-\d+', path.read_text()), f'Nonportable runtime path: {name}'

for document in [ROOT / 'README.md', ROOT / 'docs/DEVELOPMENT.md']:
    text = document.read_text()
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text)
    links += re.findall(r'<img[^>]+src="([^"]+)"', text)
    for link in links:
        if link.startswith(('https://', 'http://', '#')):
            continue
        assert (document.parent / link.split('#', 1)[0]).is_file(), f'Broken link: {link}'
for asset in (ROOT / 'docs/images').glob('*.svg'):
    ET.parse(asset)
assert len(list((ROOT / 'docs/images').glob('*.png'))) == 4
assert 'MIT License' in (ROOT / 'LICENSE').read_text()
print('PASS standalone release files, runtime parity, relative assets, SVG and source paths')
