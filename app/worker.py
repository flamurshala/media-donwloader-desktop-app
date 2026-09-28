import multiprocessing
import queue
import subprocess
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from app.downloader import process_entry, publish
from app.utils import friendly_error


class Worker(QThread):
    event = Signal(str, object)

    def __init__(self, kind, payload):
        super().__init__()
        self.kind, self.payload = kind, payload
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def run(self):
        process = None
        messages = None
        try:
            destination = Path(self.payload['directory']) if self.kind == 'download' else None
            if destination:
                destination.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.media-downloader-', dir=destination) as stage:
                ctx = multiprocessing.get_context('spawn')
                messages = ctx.Queue()
                process = ctx.Process(target=process_entry, args=(self.kind, self.payload, stage, messages))
                process.start()
                result = None
                failed = False
                while True:
                    if self.cancelled.is_set():
                        if process.is_alive():
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                            process.join(5)
                            if process.is_alive():
                                process.terminate()
                                process.join()
                        self.event.emit('cancelled', None)
                        return
                    try:
                        event, value = messages.get(timeout=0.1)
                        if event == 'result':
                            result = value
                        else:
                            failed |= event == 'error'
                            self.event.emit(event, value)
                    except queue.Empty:
                        if not process.is_alive():
                            break
                process.join()
                if result is not None and not failed:
                    if destination:
                        self.event.emit('processing', 'Saving completed files…')
                        result['files'] = publish([(Path(p), s) for p, s in result.pop('outputs')], destination, result['title'])
                    self.event.emit('result', result)
                elif not failed:
                    self.event.emit('error', 'The media worker stopped unexpectedly. Please try again.')
        except Exception as exc:
            self.event.emit('error', friendly_error(exc))
        finally:
            if process and process.is_alive():
                process.terminate()
                process.join()
            if messages:
                messages.close()
