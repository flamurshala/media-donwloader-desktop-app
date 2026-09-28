import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import APP_NAME, APP_VERSION

if __name__ == '__main__':
    version = tuple(int(x) for x in APP_VERSION.split('.')) + (0,)
    (ROOT / 'installer/version.iss').write_text(f'#define AppName "{APP_NAME}"\n#define AppVersion "{APP_VERSION}"\n', encoding='utf-8')
    (ROOT / 'installer/version_info.txt').write_text(f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version}, prodvers={version}, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription', '{APP_NAME}'), StringStruct('FileVersion', '{APP_VERSION}'), StringStruct('ProductName', '{APP_NAME}'), StringStruct('ProductVersion', '{APP_VERSION}')])]), VarFileInfo([VarStruct('Translation', [1033,1200])])])''', encoding='utf-8')
    for name in ('build', 'dist/MediaDownloader'):
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT):
            raise RuntimeError('Unsafe build cleanup path')
        if target.exists():
            shutil.rmtree(target)
    subprocess.run([sys.executable, 'tools/make_icon.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'tools/collect_licenses.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'MediaDownloader.spec'], cwd=ROOT, check=True)
    print(ROOT / 'dist/MediaDownloader/MediaDownloader.exe')
