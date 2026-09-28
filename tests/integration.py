"""Real HTTP downloads and FFmpeg processing against generated test media."""
import functools
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.downloader import download, metadata, publish
from app.utils import ffmpeg_path


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        subprocess.run([str(ffmpeg_path()), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '2', '-c:v', 'libx264', '-c:a', 'aac', str(cls.root / 'sample.mp4')], check=True, capture_output=True)
        subprocess.run([str(ffmpeg_path()), '-v', 'error', '-i', str(cls.root / 'sample.mp4'), '-an', '-c:v', 'copy', str(cls.root / 'video.mp4')], check=True, capture_output=True)
        subprocess.run([str(ffmpeg_path()), '-v', 'error', '-i', str(cls.root / 'sample.mp4'), '-vn', '-c:a', 'copy', str(cls.root / 'audio.m4a')], check=True, capture_output=True)
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(cls.root)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp.cleanup()

    def probe(self, path):
        r = subprocess.run([str(ffmpeg_path().with_name('ffprobe.exe')), '-v', 'error', '-show_streams', '-of', 'json', str(path)], capture_output=True, check=True)
        return {s['codec_type'] for s in json.loads(r.stdout)['streams']}

    def test_metadata_direct(self):
        info = metadata(self.base + '/sample.mp4')
        self.assertTrue(info['title'])

    def run_mode(self, mode, fmt, adaptive=False):
        events = []
        request = dict(url=self.base + '/sample.mp4', mode=mode, format=fmt, height=None, compatible=True)
        with tempfile.TemporaryDirectory() as stage:
            if adaptive:
                info = dict(id='local-test', title='Tëst title', webpage_url=request['url'], extractor='generic', extractor_key='Generic', formats=[
                    dict(format_id='v', url=self.base + '/video.mp4', ext='mp4', vcodec='avc1', acodec='none', height=180, fps=30),
                    dict(format_id='a', url=self.base + '/audio.m4a', ext='m4a', vcodec='none', acodec='mp4a', abr=128)])
                # Real extract_info(download=False) includes default merged streams;
                # these must be discarded before choosing an individual format.
                info['requested_formats'] = [dict(format_id='stale', url=self.base + '/must-not-download.mp4', ext='mp4', vcodec='avc1', acodec='none')]
                with patch('app.downloader.extract', return_value=info):
                    result = download(request, stage, lambda e, v: events.append((e, v)))
            else:
                result = download(request, stage, lambda e, v: events.append((e, v)))
            paths = [Path(p) for p, suffix in result['outputs']]
            expected = [{'video'}, {'audio'}] if mode.startswith('Separate') else [{'video', 'audio'}] if mode == 'Video + Audio' else [{'video'}] if mode == 'Video Only' else [{'audio'}]
            self.assertEqual([self.probe(p) for p in paths], expected)
            self.assertTrue(any(e == 'progress' for e, v in events))
            if mode == 'Video + Audio' and fmt == 'WebM' and not adaptive:
                self.assertEqual(paths[0].suffix, '.mkv')

    def test_all_modes_muxed_source(self):
        for mode, fmt in [('Video + Audio', 'MP4'), ('Video + Audio', 'MKV'), ('Video + Audio', 'WebM'), ('Video Only', 'Original'), ('Separate Video + Audio', 'Original'), *[('Audio Only', f) for f in ['Original', 'MP3', 'M4A', 'WAV', 'FLAC']]]:
            with self.subTest(mode=mode, format=fmt):
                self.run_mode(mode, fmt)

    def test_all_modes_adaptive_source(self):
        for mode, fmt in [('Video + Audio', 'MP4'), ('Video Only', 'Original'), ('Separate Video + Audio', 'Original'), ('Audio Only', 'Original')]:
            with self.subTest(mode=mode):
                self.run_mode(mode, fmt, True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
