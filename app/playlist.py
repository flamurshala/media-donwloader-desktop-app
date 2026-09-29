"""Small playlist metadata and naming helpers shared by the UI and supervisor."""
import re
from urllib.parse import urlsplit, parse_qs


def is_playlist(info: dict) -> bool:
    return info.get('_type') in ('playlist', 'multi_video') or 'entries' in info


def safe_folder(title: str) -> str:
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip('. ')[:100].rstrip('. ')
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)', title, re.I):
        title = '_' + title
    return title or 'Untitled playlist'


def entry_url(entry: dict) -> str | None:
    url = entry.get('webpage_url') or entry.get('url') or ''
    parsed = urlsplit(url)
    if parsed.hostname and (parsed.hostname == 'youtu.be' or parsed.hostname.endswith('.youtube.com') or parsed.hostname == 'youtube.com'):
        video_id = parse_qs(parsed.query).get('v', [None])[0] or (parsed.path.strip('/') if parsed.hostname == 'youtu.be' else None) or entry.get('id')
        return f'https://www.youtube.com/watch?v={video_id}' if video_id else None
    if url.startswith(('https://', 'http://')):
        return url
    video_id = entry.get('id') or url
    return f'https://www.youtube.com/watch?v={video_id}' if video_id else None


def playlist_metadata(info: dict) -> dict:
    entries = []
    for position, raw in enumerate(info.get('entries') or [], 1):
        entry = raw or {}
        title = entry.get('title') or 'Unavailable video'
        unavailable = not raw or title.lower() in ('[private video]', '[deleted video]', 'private video', 'deleted video') or entry.get('availability') in ('private', 'premium_only', 'subscriber_only', 'needs_auth')
        entries.append(dict(index=entry.get('playlist_index') or position, title=title, url=entry_url(entry), unavailable=unavailable))
    if not entries:
        raise ValueError('This playlist is empty or its entries are unavailable.')
    return dict(is_playlist=True, title=info.get('title') or 'Untitled playlist', uploader=info.get('uploader') or info.get('channel') or 'Unknown creator', duration=None, qualities=[2160, 1440, 1080, 720, 480, 360], entries=entries, entry_count=len(entries))


def numbered_title(entry: dict, total: int) -> str:
    return f"{entry['index']:0{max(3, len(str(total)), len(str(entry['index'])))}d} - {entry['title']}"


def overall_progress(processed: int, total: int) -> int:
    return min(100, max(0, int(processed * 100 / total))) if total else 0


def fatal_error(error: Exception) -> bool:
    text = str(error).lower()
    return isinstance(error, (PermissionError, OSError)) or any(word in text for word in ('no space left', 'disk full', 'not enough space', 'permission denied', 'access is denied', 'bundled ffmpeg is missing', 'winerror 193', 'winerror 112'))
