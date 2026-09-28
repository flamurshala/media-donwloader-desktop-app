import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit


def resource_path(name):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / name


def ffmpeg_path():
    path = resource_path('vendor/ffmpeg/ffmpeg.exe')
    if not path.is_file() or not path.with_name('ffprobe.exe').is_file():
        raise ValueError('Bundled FFmpeg is missing. Please reinstall Media Downloader.')
    return path


def valid_url(value):
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
    except ValueError:
        raise ValueError('Enter a valid http:// or https:// video URL.') from None
    return value


def duration(seconds):
    if seconds is None:
        return '—'
    seconds = max(0, int(seconds))
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f'{h}:{m:02}:{s:02}' if h else f'{m:02}:{s:02}'


def size(value):
    if value is None:
        return '—'
    value = max(0, value)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB':
            return f'{value:.0f} B' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


def setup_logging(worker=False):
    folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MediaDownloader' / 'logs'
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / ('worker.log' if worker else 'application.log'), maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def friendly_error(error):
    text = str(error).lower()
    for needles, message in (
        (('certificate', 'ssl:'), 'A secure connection could not be verified. Check Windows date/time and your network certificate configuration.'),
        (('403', 'forbidden'), 'The website refused access to this media. Try fetching again or another video. This version does not support login or access tokens.'),
        (('private', 'sign in', 'login', 'age-restricted', 'cookies'), 'This content requires authentication. Login and cookies are not supported in this version.'),
        (('drm', 'protected'), 'This content is protected by DRM and cannot be downloaded.'),
        (('unsupported url',), 'This website or URL is not supported. Try a direct video page.'),
        (('format', 'no video', 'no audio'), 'The requested media format is unavailable. Fetch again or choose Best / another format.'),
        (('timed out', 'resolve', 'connection', 'network'), 'The connection failed. Check your internet connection and try again.'),
        (('space', 'disk full'), 'There is not enough free disk space in the destination.'),
        (('permission', 'access is denied'), 'Cannot write to this folder. Choose a folder you have permission to use.'),
        (('unavailable', 'removed', '404'), 'This video is unavailable or has been removed.'),
    ):
        if any(n in text for n in needles):
            return message
    if isinstance(error, ValueError):
        return str(error)
    return 'The operation could not be completed. Check your connection, fetch again, or try another video. Technical information was saved in the application log.'


class SafeLogger:
    # Keep diagnostics without retaining URL tokens, cookies or request headers.
    def debug(self, message):
        pass

    def warning(self, message):
        logging.warning('yt-dlp: %s', re.sub(r'https?://\S+', '[URL]', str(message)))

    error = warning
