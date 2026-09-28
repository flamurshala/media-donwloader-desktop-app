"""Obtain pinned, official release dependencies. HTTPS verification stays enabled."""
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / 'vendor'


def get(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    print('Downloading', url, flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, target.open('wb') as output:
        shutil.copyfileobj(response, output)
    return target


def release(repo, tag, asset_name, target):
    with urllib.request.urlopen(f'https://api.github.com/repos/{repo}/releases/tags/{tag}', timeout=30) as response:
        data = json.load(response)
    asset = next(a for a in data['assets'] if a['name'] == asset_name)
    get(asset['browser_download_url'], target)
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    expected = asset.get('digest')
    if expected and expected != 'sha256:' + digest:
        raise RuntimeError('Release digest mismatch: ' + asset_name)
    record = dict(url=asset['browser_download_url'], sha256=digest, upstream_digest=expected)
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(record, indent=2))
    print('SHA256', digest, flush=True)


if __name__ == '__main__':
    VENDOR.mkdir(exist_ok=True)
    release('GyanD/codexffmpeg', '9.0.2', 'ffmpeg-9.0.2-essentials_build.zip', VENDOR / 'ffmpeg.zip')
    with zipfile.ZipFile(VENDOR / 'ffmpeg.zip') as archive:
        for name in archive.namelist():
            if Path(name).name in ('ffmpeg.exe', 'ffprobe.exe', 'LICENSE', 'README.txt'):
                target = VENDOR / 'ffmpeg' / Path(name).name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(archive.read(name))
    release('denoland/deno', 'v2.9.7', 'deno-x86_64-pc-windows-msvc.zip', VENDOR / 'deno.zip')
    with zipfile.ZipFile(VENDOR / 'deno.zip') as archive:
        (VENDOR / 'deno').mkdir(exist_ok=True)
        (VENDOR / 'deno/deno.exe').write_bytes(archive.read('deno.exe'))
    get('https://raw.githubusercontent.com/denoland/deno/v2.9.7/LICENSE.md', VENDOR / 'deno/LICENSE.md')
    release('jrsoftware/issrc', 'is-7_1_0', 'innosetup-7.1.0-x64.exe', ROOT / 'tools/innosetup.exe')
