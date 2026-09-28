import os
from pathlib import Path
import pefile

root = Path('dist/MediaDownloader/_internal')
paths = {p.name.lower(): p for p in root.rglob('*.dll')}
cache = {}
for source in [root / 'PySide6/QtCore.pyd', *root.rglob('Qt6Core.dll'), *root.rglob('pyside6.abi3.dll'), *root.rglob('shiboken6.abi3.dll')]:
    pe = pefile.PE(str(source))
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        name = entry.dll.decode().lower()
        target = paths.get(name, Path(os.environ['SystemRoot']) / 'System32' / name)
        if not target.exists():
            continue
        if name not in cache:
            other = pefile.PE(str(target))
            cache[name] = {s.name for s in other.DIRECTORY_ENTRY_EXPORT.symbols} if hasattr(other, 'DIRECTORY_ENTRY_EXPORT') else set()
        missing = [s.name.decode() for s in entry.imports if s.name and s.name not in cache[name]]
        if missing:
            print(source.name, '->', target, missing)
