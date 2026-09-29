"""Opt-in packaged end-to-end verification, invoked by the developer test runner."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox


def integration(app, window, url, output, report):
    state = {'phase': 'fetch', 'events': []}
    report = Path(report)
    def finish(error=None):
        timer.stop()
        report.write_text(json.dumps(dict(success=not error, error=error, files=[str(p) for p in Path(output).rglob('*') if p.is_file()], events=state['events'], summary=state.get('summary')), indent=2))
        window.grab().save(str(report.with_suffix('.png')))
        app.quit()
    def event(kind, value):
        state['events'].append(kind)
        if kind == 'playlist_finished':
            state['summary'] = value
            if value['error'] or value['failed']:
                state['error'] = value['error'] or 'Playlist entries failed'
        if kind == 'error':
            state['error'] = value
    def tick():
        for dialog in app.topLevelWidgets():
            if isinstance(dialog, QMessageBox):
                dialog.accept()
        if window.worker:
            return
        if state.get('error'):
            finish(state['error'])
        elif state['phase'] == 'fetch':
            if not window.info:
                finish('Metadata unavailable')
                return
            window.mode.setCurrentText('Video + Audio')
            window.format.setCurrentText('MP4')
            window.directory.setText(output)
            window.download()
            window.worker.event.connect(event)
            state['phase'] = 'download'
        else:
            finish(None if window.last_folder else 'No completed output')
    if Path(url).is_file():
        # Explicit developer-only fixture for packaged queue tests. Downloads
        # still use real spawned workers, HTTP, yt-dlp and bundled FFmpeg.
        from app.playlist import playlist_metadata
        from app.worker import Worker
        info = playlist_metadata(json.loads(Path(url).read_text(encoding='utf-8')))
        window.worker = Worker('fetch', {})
        window.on_event('result', info | dict(thumbnail=b''))
        window.worker = None
    else:
        window.url.setText(url)
        window.fetch()
        window.worker.event.connect(event)
    timer = QTimer(window)
    timer.timeout.connect(tick)
    timer.start(100)
    QTimer.singleShot(90000, lambda: finish('Timed out') if timer.isActive() else None)
