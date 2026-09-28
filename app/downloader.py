import logging
import json
import os
import re
import shutil
import subprocess
import urllib.request
import traceback
from pathlib import Path

import yt_dlp
from yt_dlp.utils import sanitize_filename

from app.formats import qualities, select_audio, select_video
from app.utils import SafeLogger, ffmpeg_path, friendly_error, resource_path, setup_logging


def options():
    return dict(noplaylist=True, quiet=True, no_warnings=True, logger=SafeLogger(), socket_timeout=20,
                retries=3, fragment_retries=3, windowsfilenames=True, cachedir=False,
                compat_opts={'no-certifi'},  # Honor trusted Windows roots, including managed-network CAs.
                ffmpeg_location=str(resource_path('vendor/ffmpeg')),
                js_runtimes={'deno': {'path': str(resource_path('vendor/deno/deno.exe'))}})


def extract(url):
    with yt_dlp.YoutubeDL(options()) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info or info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
        raise ValueError('Please paste an individual video URL. Playlist downloads are not supported.')
    if info.get('is_live'):
        raise ValueError('Live streams are not supported in this version. Try a finished video.')
    # Generic direct-media URLs may not advertise codecs until the file is read.
    for fmt in info.get('formats') or [info]:
        if not fmt.get('vcodec') and not fmt.get('acodec'):
            fmt['vcodec'] = 'none' if fmt.get('ext') in ('mp3', 'm4a', 'aac', 'ogg', 'opus', 'wav', 'flac') else 'unknown'
            fmt['acodec'] = 'unknown'
        fmt.setdefault('format_id', fmt.get('ext') or 'direct')
    return info


def metadata(url):
    info = extract(url)
    thumbnail = b''
    if info.get('thumbnail', '').startswith(('https://', 'http://')):
        try:
            with urllib.request.urlopen(info['thumbnail'], timeout=8) as response:
                thumbnail = response.read(5_000_001)
            if len(thumbnail) > 5_000_000:
                thumbnail = b''
        except Exception:
            logging.info('Thumbnail unavailable')
    return dict(title=info.get('title') or 'Untitled video', uploader=info.get('uploader') or info.get('channel') or 'Unknown creator',
                duration=info.get('duration'), qualities=qualities(info.get('formats') or [info]), thumbnail=thumbnail)


def media_command(args):
    result = subprocess.run([str(ffmpeg_path()), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', *map(str, args)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        logging.error('FFmpeg failed: %s', result.stderr.decode('utf-8', errors='replace')[-2000:])
        raise ValueError('FFmpeg could not process this media. Try MKV or a different audio format.')


def publish(files, destination, title):
    """Reserve all output names exclusively; roll back only files we own on failure."""
    title = sanitize_filename(title, restricted=False).strip('. ')[:110] or 'Untitled video'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)', title, re.IGNORECASE):
        title = '_' + title
    owned = []
    try:
        for source, suffix in files:
            index = 0
            while True:
                extra = f' ({index})' if index else ''
                target = destination / f'{title}{suffix}{extra}{source.suffix}'
                try:
                    output = target.open('xb')
                    break
                except FileExistsError:
                    index += 1
            owned.append(target)
            with output, source.open('rb') as inp:
                shutil.copyfileobj(inp, output, 1024 * 1024)
        return [str(p) for p in owned]
    except BaseException:
        for target in owned:
            target.unlink(missing_ok=True)
        raise


def download(request, stage, emit):
    stage = Path(stage)
    emit('status', 'Checking available streams…')
    info = extract(request['url'])
    formats = info.get('formats') or [info]
    mode, container = request['mode'], request['format'].lower()
    video = None if mode == 'Audio Only' else select_video(formats, request['height'], request['compatible'], container)
    audio = None if mode == 'Video Only' else select_audio(formats, request['compatible'] and container == 'mp4')
    # Fail before downloading large files when the requested operation needs FFmpeg.
    if mode == 'Video + Audio' or (video and video.get('acodec') != 'none') or (audio and (audio.get('vcodec') != 'none' or container != 'original' and mode == 'Audio Only')):
        ffmpeg_path()
    notes = []
    if video and request['height'] and video.get('height') != request['height']:
        notes.append(f"Selected quality is no longer available; downloaded {video.get('height', 'unknown')}p.")

    def fetch(fmt, label):
        emit('status', f'Downloading {label}…')
        def hook(data):
            if data['status'] == 'downloading':
                emit('progress', {k: data.get(k) for k in ('downloaded_bytes', 'total_bytes', 'total_bytes_estimate', 'speed', 'eta')})
        opts = options() | {'format': str(fmt['format_id']), 'outtmpl': str(stage / (label + '.%(ext)s')), 'progress_hooks': [hook]}
        # Already-extracted information retains site-specific headers and downloader options.
        with yt_dlp.YoutubeDL(opts) as ydl:
            stream_info = dict(info)
            # extract_info(download=False) still adds its default selected streams.
            # Do not carry those into a new single-stream selection (yt-dlp would
            # otherwise download the previous merged selection).
            stream_info.pop('requested_formats', None)
            stream_info.pop('requested_downloads', None)
            result = ydl.process_ie_result(stream_info, download=True)
            path = Path(result.get('requested_downloads', [{}])[0].get('filepath') or ydl.prepare_filename(result))
        if not path.is_file():
            raise ValueError('The downloaded media file could not be found.')
        return path

    def fetch_available(selected, label):
        remaining = list(formats)
        for attempt in range(4):
            try:
                return selected, fetch(selected, f'{label}-{attempt + 1}')
            except yt_dlp.utils.DownloadError as exc:
                # Sites sometimes advertise stale/unavailable CDN variants. Retry
                # another advertised stream, preserving the exact video height.
                if attempt == 3 or not any(code in str(exc).lower() for code in ('403', '404', 'format is not available')):
                    raise
                remaining = [f for f in remaining if f.get('format_id') != selected.get('format_id')]
                if label == 'video':
                    remaining = [f for f in remaining if f.get('height') == selected.get('height')]
                    selected = select_video(remaining, request['height'], False, 'mkv')
                else:
                    selected = select_audio(remaining, False)
                emit('status', f'Trying another available {label} stream…')
        raise ValueError('No usable media format is available.')

    if video:
        video, vp = fetch_available(video, 'video')
    else:
        vp = None
    if audio and video and audio['format_id'] == video['format_id']:
        ap = vp
    elif audio:
        audio, ap = fetch_available(audio, 'audio')
    else:
        ap = None
    for fmt, path in ((video, vp), (audio, ap)):
        if fmt and 'unknown' in (fmt.get('vcodec'), fmt.get('acodec')):
            probe = subprocess.run([str(ffmpeg_path().with_name('ffprobe.exe')), '-v', 'error', '-show_streams', '-of', 'json', str(path)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            streams = json.loads(probe.stdout)['streams']
            fmt['vcodec'] = next((s['codec_name'] for s in streams if s['codec_type'] == 'video'), 'none')
            fmt['acodec'] = next((s['codec_name'] for s in streams if s['codec_type'] == 'audio'), 'none')
    if video and video['vcodec'] == 'none':
        raise ValueError('No video stream is present in this media.')
    if audio and audio['acodec'] == 'none':
        raise ValueError('No audio stream is present in this media. Choose Video Only.')
    if video and request['compatible'] and container == 'mp4' and not video.get('vcodec', '').startswith(('avc', 'h264')):
        notes.append('The preferred H.264 stream was unavailable at this resolution. Another original video codec was retained without reducing resolution.')
    outputs = []
    emit('processing', 'Processing media…')
    if mode == 'Video + Audio':
        vc, ac = video.get('vcodec', ''), audio.get('acodec', '')
        if container == 'webm' and not (vc.startswith(('vp8', 'vp9', 'vp0', 'av01')) and ac.startswith(('opus', 'vorbis'))):
            container = 'mkv'
            notes.append('These streams do not fit WebM. Saved MKV to preserve quality without re-encoding.')
        if container == 'mp4' and not (vc.startswith(('avc', 'h264', 'hev', 'h265', 'av01', 'vp9', 'vp0', 'mpeg4')) and ac.startswith(('mp4a', 'aac', 'mp3', 'opus', 'ac3', 'eac3', 'alac'))):
            container = 'mkv'
            notes.append('These codecs require MKV. Saved MKV without re-encoding.')
        out = stage / f'final.{container}'
        emit('processing', 'Merging video and audio…')
        media_command(['-i', vp, '-i', ap, '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy', out])
        outputs.append((out, ''))
    else:
        if vp:
            if video.get('acodec') not in (None, 'none'):
                out = stage / 'silent.mkv'
                media_command(['-i', vp, '-map', '0:v:0', '-c:v', 'copy', '-an', out])
                vp = out
            outputs.append((vp, ' - video' if mode.startswith('Separate') else ''))
        if ap:
            audio_format = container if mode == 'Audio Only' else 'original'
            if audio_format != 'original' or audio.get('vcodec') not in (None, 'none'):
                ext = audio_format if audio_format != 'original' else ('m4a' if audio.get('acodec', '').startswith(('aac', 'mp4a')) else 'mka')
                out = stage / f'extracted.{ext}'
                codec = {'mp3': ['libmp3lame', '-b:a', '192k'], 'wav': ['pcm_s16le'], 'flac': ['flac'], 'm4a': ['copy'] if audio.get('acodec', '').startswith(('aac', 'mp4a')) else ['aac', '-b:a', '192k']}.get(audio_format, ['copy'])
                emit('processing', 'Extracting / converting audio…')
                media_command(['-i', ap, '-map', '0:a:0', '-vn', '-c:a', *codec, out])
                ap = out
            outputs.append((ap, ' - audio' if mode.startswith('Separate') else ''))
    # Publication happens in the supervisor after the child exits, so cancellation
    # cannot kill the process halfway through writing a final user file.
    return dict(outputs=[(str(p), suffix) for p, suffix in outputs], title=info.get('title') or 'Untitled video', notes=notes)


def process_entry(kind, payload, stage, queue):
    setup_logging(worker=True)
    def emit(event, value):
        queue.put((event, value))
    try:
        result = metadata(payload['url']) if kind == 'fetch' else download(payload, stage, emit)
        emit('result', result)
    except Exception as exc:
        logging.error('%s failed (%s): %s', kind, type(exc).__name__, friendly_error(exc))
        logging.error('%s', re.sub(r'https?://\S+', '[URL]', traceback.format_exc()))
        emit('error', friendly_error(exc))
