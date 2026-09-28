import tempfile
import unittest
from pathlib import Path
from app.formats import qualities, select_audio, select_video
from app.downloader import publish
from app.utils import duration, size, valid_url


def fmt(height, codec='avc1', fps=30, **extra):
    return dict(height=height, vcodec=codec, acodec='none', url='http://localhost/v', fps=fps, **extra)


class CoreTests(unittest.TestCase):
    def test_qualities(self):
        self.assertEqual(qualities([fmt(2160), fmt(1080), fmt(1080), fmt(720), fmt(None), fmt(480, has_drm=True), fmt(999, codec='none')]), [2160, 1080, 720])

    def test_resolution_before_compatibility(self):
        self.assertEqual(select_video([fmt(1080), fmt(2160, 'vp9')], 2160)['height'], 2160)

    def test_fps_and_compatibility(self):
        self.assertEqual(select_video([fmt(1080, fps=30), fmt(1080, fps=60)])['fps'], 60)
        self.assertEqual(select_video([fmt(1080, 'vp9'), fmt(1080)])['vcodec'], 'avc1')

    def test_fallback_never_exceeds(self):
        self.assertEqual(select_video([fmt(2160), fmt(720)], 1080)['height'], 720)
        with self.assertRaises(ValueError):
            select_video([fmt(2160)], 1080)

    def test_audio(self):
        self.assertEqual(select_audio([dict(url='x', vcodec='none', acodec='opus', abr=160), dict(url='x', vcodec='none', acodec='mp4a', abr=128)], True)['acodec'], 'mp4a')

    def test_extractor_ranking_beats_manifest_bitrate(self):
        hls = fmt(144, protocol='m3u8_native', tbr=170)
        direct = fmt(144, protocol='https', tbr=54)
        self.assertIs(select_video([hls, direct], 144), direct)

    def test_urls(self):
        self.assertEqual(valid_url(' https://example.org/a '), 'https://example.org/a')
        for value in ('', 'file:///a', 'hello', 'https://', 'https://user:password@example.org'):
            with self.assertRaises(ValueError):
                valid_url(value)

    def test_formatting(self):
        self.assertEqual(duration(3800), '1:03:20')
        self.assertEqual(duration(31), '00:31')
        self.assertEqual(size(1024), '1.0 KB')

    def test_safe_publication_unicode_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / 'input.mp4'
            source.write_bytes(b'media')
            first = publish([(source, '')], directory, 'Tëst: / title')
            second = publish([(source, '')], directory, 'Tëst: / title')
            self.assertNotEqual(first, second)
            self.assertEqual(Path(first[0]).read_bytes(), b'media')
            self.assertEqual(Path(second[0]).read_bytes(), b'media')

    def test_reserved_windows_names(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / 'input.mp4'
            source.write_bytes(b'media')
            for title in ('CON', 'AUX', 'NUL', 'COM1', 'LPT9', 'con.hidden'):
                result = publish([(source, '')], directory, title)
                self.assertTrue(Path(result[0]).name.startswith('_'))
                self.assertEqual(Path(result[0]).read_bytes(), b'media')


if __name__ == '__main__':
    unittest.main()
