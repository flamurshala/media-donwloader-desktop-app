"""Opt-in packaged end-to-end verification, invoked by the developer test runner."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer


def integration(app, window, url, output, report):
    state = {'phase': 'fetch', 'events': []}
    report = Path(report)
    def finish(error=None):
        timer.stop()
        report.write_text(json.dumps(dict(success=not error, error=error, files=[str(p) for p in Path(output).glob('*') if p.is_file()], events=state['events']), indent=2))
        window.grab().save(str(report.with_suffix('.png')))
        app.quit()
    def event(kind, value):
        state['events'].append(kind)
        if kind == 'error':
            state['error'] = value
    def tick():
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
    window.url.setText(url)
    window.fetch()
    window.worker.event.connect(event)
    timer = QTimer(window)
    timer.timeout.connect(tick)
    timer.start(100)
    QTimer.singleShot(90000, lambda: finish('Timed out') if timer.isActive() else None)
