import functools
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from app.worker import Worker
from app.utils import ffmpeg_path

ROOT = Path(__file__).resolve().parent.parent


def slow_ffmpeg_target(kind, payload, stage, queue):
    child = subprocess.Popen([str(ffmpeg_path()), '-v', 'error', '-re', '-stream_loop', '-1', '-i', payload['sample'], '-f', 'null', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    queue.put(('ffmpeg_pid', child.pid))
    child.wait()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/slow.mp4':
            time.sleep(8)
            self.path = '/sample.mp4'
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        subprocess.run([str(ffmpeg_path()), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30', '-f', 'lavfi', '-i', 'sine', '-t', '2', '-c:v', 'libx264', '-c:a', 'aac', str(cls.root / 'sample.mp4')], capture_output=True, check=True)
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(cls.root)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        # Slow test responses may still be unwinding after client cancellation.
        cls.temp.cleanup()

    def wait_worker(self, worker, timeout=20):
        deadline = time.monotonic() + timeout
        while worker.isRunning() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.02)
        self.app.processEvents()
        self.assertFalse(worker.isRunning())

    def test_cancel_cleans_stage_preserves_existing(self):
        dest = self.root / 'cancel'
        dest.mkdir()
        old = dest / 'existing.mp4'
        old.write_bytes(b'existing')
        events = []
        worker = Worker('download', dict(url=self.url + '/slow.mp4', directory=str(dest), mode='Video + Audio', format='MP4', height=None, compatible=True))
        worker.event.connect(lambda k, v: events.append(k))
        worker.start()
        until = time.monotonic() + 1
        while time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.02)
        worker.cancel()
        self.wait_worker(worker)
        self.assertIn('cancelled', events)
        self.assertEqual(old.read_bytes(), b'existing')
        self.assertEqual(list(dest.iterdir()), [old])

    def test_failed_worker_recovers(self):
        events = []
        worker = Worker('fetch', {'url': self.url + '/missing.mp4'})
        worker.event.connect(lambda k, v: events.append(k))
        worker.start()
        self.wait_worker(worker)
        self.assertIn('error', events)

    def test_cancel_stops_ffmpeg_child(self):
        events = []
        worker = Worker('fetch', {'sample': str(self.root / 'sample.mp4')})
        worker.event.connect(lambda k, v: events.append((k, v)))
        with patch('app.worker.process_entry', slow_ffmpeg_target):
            worker.start()
            deadline = time.monotonic() + 15
            while not events and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.02)
            worker.cancel()
            self.wait_worker(worker)
        pid = next(v for k, v in events if k == 'ffmpeg_pid')
        listing = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertNotIn(str(pid), listing.stdout)

    def test_source_gui_download(self):
        self.run_gui([sys.executable, str(ROOT / 'run.py')], 'source')

    @unittest.skipUnless((ROOT / 'dist/MediaDownloader/MediaDownloader.exe').exists(), 'Executable not built yet')
    def test_frozen_gui_download(self):
        self.run_gui([str(ROOT / 'dist/MediaDownloader/MediaDownloader.exe')], 'frozen')

    def run_gui(self, command, name):
        output = ROOT / 'test-output' / (name + '-download')
        output.mkdir(parents=True, exist_ok=True)
        report = ROOT / 'test-output' / (name + '-integration.json')
        subprocess.run(command + ['--integration-test', self.url + '/sample.mp4', str(output), str(report)], timeout=100, check=True)
        result = json.loads(report.read_text())
        self.assertTrue(result['success'], result)
        self.assertIn('progress', result['events'])
        self.assertTrue(any(Path(p).suffix == '.mp4' for p in result['files']))


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    unittest.main(verbosity=2)
