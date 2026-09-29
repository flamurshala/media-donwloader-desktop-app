import json
import hashlib
import logging
import multiprocessing
import queue
import subprocess
import tempfile
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from app.downloader import process_entry, publish
from app.playlist import safe_folder, numbered_title, overall_progress
from app.utils import friendly_error


class Cancelled(Exception):
    pass


class ItemError(Exception):
    def __init__(self, value):
        self.fatal = isinstance(value, dict) and value.get('fatal', False)
        super().__init__(value['message'] if isinstance(value, dict) else value)


class Worker(QThread):
    event = Signal(str, object)

    def __init__(self, kind, payload):
        super().__init__()
        self.kind, self.payload = kind, payload
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def operation(self, kind, payload, destination=None, title=None):
        process = messages = stage_temp = None
        try:
            if destination:
                destination.mkdir(parents=True, exist_ok=True)
            stage_temp = tempfile.TemporaryDirectory(prefix='.media-downloader-', dir=destination)
            stage = stage_temp.name
            if self.cancelled.is_set():
                raise Cancelled()
            ctx = multiprocessing.get_context('spawn')
            messages = ctx.Queue()
            process = ctx.Process(target=process_entry, args=(kind, payload, stage, messages))
            process.start()
            result = failure = None
            while True:
                if self.cancelled.is_set():
                    raise Cancelled()
                try:
                    event, value = messages.get(timeout=0.1)
                    if event == 'result':
                        result = value
                    elif event == 'error':
                        failure = value
                    else:
                        self.event.emit(event, value)
                except queue.Empty:
                    if not process.is_alive():
                        break
            process.join()
            if failure is not None:
                raise ItemError(failure)
            if result is None:
                raise ItemError('The media worker stopped unexpectedly. Please try again.')
            if self.cancelled.is_set():
                raise Cancelled()
            if destination:
                self.event.emit('processing', 'Saving completed files…')
                result['files'] = publish([(Path(p), s) for p, s in result.pop('outputs')], destination, title or result['title'])
            return result
        finally:
            # Stop FFmpeg descendants before TemporaryDirectory removes active files.
            if process and process.is_alive():
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                process.join(5)
                if process.is_alive():
                    process.terminate()
                    process.join()
            if messages:
                messages.close()
            if stage_temp:
                stage_temp.cleanup()

    def playlist(self):
        info = self.payload['playlist']
        destination = Path(self.payload['directory']) / safe_folder(info['title'])
        summary = dict(title=info['title'], total=len(info['entries']), downloaded=0, skipped=0, failed=0, details=[], folder=str(destination), cancelled=False, error=None)
        try:
            destination.mkdir(parents=True, exist_ok=True)
            # A local receipt is scoped to URL, ordering and download settings. Only
            # files successfully published by this app are eligible for restart skips.
            receipt = destination / '.media-downloader-receipts.json'
            try:
                records = json.loads(receipt.read_text(encoding='utf-8'))
                if not isinstance(records, dict):
                    records = {}
            except (OSError, ValueError):
                records = {}
            with tempfile.TemporaryFile(dir=destination):
                pass  # Detect an unwritable destination before starting the queue.
            for position, entry in enumerate(info['entries'], 1):
                if self.cancelled.is_set():
                    raise Cancelled()
                self.event.emit('current_item', dict(position=position, total=summary['total'], title=entry['title']))
                key = hashlib.sha256(json.dumps([entry, self.payload['mode'], self.payload['format'], self.payload['height'], self.payload['compatible']], sort_keys=True).encode()).hexdigest()
                previous = records.get(key, [])
                existing = isinstance(previous, list) and bool(previous) and all(isinstance(f, dict) and Path(f.get('name', '')).name == f.get('name') and (destination / f['name']).is_file() and (destination / f['name']).stat().st_size == f.get('size') for f in previous)
                if entry['unavailable'] or not entry['url'] or existing:
                    summary['skipped'] += 1
                    reason = 'Already downloaded (matching settings).' if existing else 'Unavailable or requires access.'
                    summary['details'].append(f"#{entry['index']} - {entry['title']}: {reason}")
                    logging.info('Playlist skip: %s', summary['details'][-1])
                else:
                    try:
                        payload = self.payload | dict(url=entry['url'], playlist_item=True)
                        payload.pop('playlist', None)
                        result = self.operation('download', payload, destination, numbered_title(entry, summary['total']))
                        summary['downloaded'] += 1
                        records[key] = [dict(name=Path(p).name, size=Path(p).stat().st_size) for p in result['files']]
                        temporary = receipt.with_suffix('.tmp')
                        temporary.write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
                        temporary.replace(receipt)
                        summary['details'].extend(f"#{entry['index']}: {note}" for note in result['notes'])
                    except ItemError as exc:
                        summary['failed'] += 1
                        summary['details'].append(f"#{entry['index']} - {entry['title']}: {exc}")
                        logging.warning('Playlist item failed: %s', summary['details'][-1])
                        if exc.fatal:
                            summary['error'] = str(exc)
                            break
                processed = summary['downloaded'] + summary['skipped'] + summary['failed']
                self.event.emit('overall', summary | dict(percent=overall_progress(processed, summary['total'])))
        except Cancelled:
            summary['cancelled'] = True
        except Exception as exc:
            summary['error'] = friendly_error(exc)
        self.event.emit('playlist_finished', summary)

    def run(self):
        if self.kind == 'download' and self.payload.get('playlist'):
            self.playlist()
            return
        try:
            destination = Path(self.payload['directory']) if self.kind == 'download' else None
            self.event.emit('result', self.operation(self.kind, self.payload, destination))
        except Cancelled:
            self.event.emit('cancelled', None)
        except ItemError as exc:
            self.event.emit('error', str(exc))
        except Exception as exc:
            self.event.emit('error', friendly_error(exc))
