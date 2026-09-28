from PyInstaller.utils.hooks import collect_all, collect_data_files
from pathlib import Path
import os
import sys

# Build hosts may add unrelated graphics/PDF runtimes to PATH. Their ICU/UCRT
# DLLs must not shadow Windows system libraries during dependency collection.
os.environ['PATH'] = os.pathsep.join([str(Path(sys.executable).parent), sys.base_prefix,
                                    str(Path(os.environ['SystemRoot']) / 'System32'), os.environ['SystemRoot']])

root = Path(SPECPATH)
for item in ['vendor/ffmpeg/ffmpeg.exe', 'vendor/ffmpeg/ffprobe.exe', 'vendor/deno/deno.exe']:
    if not (root / item).is_file():
        raise SystemExit('Missing bundled dependency: ' + item + '. Run tools/setup_vendor.py.')
ejs_data, ejs_binaries, ejs_hidden = collect_all('yt_dlp_ejs')
datas = [('vendor/ffmpeg', 'vendor/ffmpeg'), ('vendor/deno', 'vendor/deno'), ('app/resources', 'app/resources'), ('LICENSES.md', '.'), ('licenses', 'licenses')] + ejs_data
a = Analysis(['run.py'], pathex=[str(root)], binaries=ejs_binaries, datas=datas,
             hiddenimports=ejs_hidden, excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MediaDownloader', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=bool(os.environ.get('MD_BUILD_CONSOLE')),
          icon='app/resources/icon.ico', version='installer/version_info.txt')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='MediaDownloader')
