def video_formats(formats):
    return [f for f in formats if f.get('vcodec') not in (None, 'none') and not f.get('has_drm') and f.get('url')]


def qualities(formats):
    return sorted({int(f['height']) for f in video_formats(formats) if isinstance(f.get('height'), (int, float)) and f['height'] > 0}, reverse=True)


def select_video(formats, height=None, compatible=True, container='mp4'):
    rank = {id(f): index for index, f in enumerate(formats)}
    candidates = video_formats(formats)
    if height:
        candidates = [f for f in candidates if 0 < (f.get('height') or 0) <= height]
    if not candidates:
        raise ValueError('No video format is available at or below the selected quality. Fetch again or choose Best.')
    def score(f):
        codec = f.get('vcodec', '')
        preferred = (codec.startswith(('avc', 'h264')) if container == 'mp4' else codec.startswith(('vp8', 'vp9', 'vp0', 'av01'))) if compatible or container == 'webm' else False
        # yt-dlp orders formats worst-to-best using protocol and extractor-specific
        # preferences. Manifest bitrate estimates must not override that ranking.
        return (f.get('height') or 0, preferred, f.get('fps') or 0, rank[id(f)])
    return max(candidates, key=score)


def select_audio(formats, compatible=False):
    rank = {id(f): index for index, f in enumerate(formats)}
    candidates = [f for f in formats if f.get('acodec') not in (None, 'none') and f.get('url') and not f.get('has_drm')]
    if not candidates:
        raise ValueError('No audio format is available for this video.')
    return max(candidates, key=lambda f: (f.get('vcodec') == 'none', compatible and f.get('acodec', '').startswith(('mp4a', 'aac')), f.get('language_preference') or 0, rank[id(f)]))
