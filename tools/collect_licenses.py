import importlib.metadata
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
folder = ROOT / 'licenses'
folder.mkdir(exist_ok=True)
packages = ['PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'yt-dlp', 'yt-dlp-ejs', 'certifi', 'requests', 'urllib3', 'idna', 'charset-normalizer', 'brotli', 'mutagen', 'pycryptodomex', 'websockets', 'pyinstaller']
for name in packages:
    dist = importlib.metadata.distribution(name)
    for item in dist.files or []:
        if any(token in str(item).lower() for token in ('license', 'copying', 'notice')) and not str(item).endswith(('.py', '.pyc', '.h', '.cpp')):
            source = Path(dist.locate_file(item))
            if source.is_file():
                target = folder / name / str(item).replace('..', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
for name in ('LICENSE.txt', 'LICENSE'):
    source = Path(sys.base_prefix) / name
    if source.exists():
        shutil.copy2(source, folder / 'Python-LICENSE.txt')
for name in ('ffmpeg/LICENSE', 'ffmpeg/README.txt', 'deno/LICENSE.md'):
    source = ROOT / 'vendor' / name
    if source.exists():
        shutil.copy2(source, folder / (name.replace('/', '-')))
