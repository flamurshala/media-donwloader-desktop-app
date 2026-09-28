import json
import logging
import subprocess
import sys
import tempfile
import ctypes
from pathlib import Path

from PySide6.QtCore import QTimer, QSettings
from PySide6.QtWidgets import QApplication, QMessageBox
import yt_dlp.version

from app.config import APP_NAME, APP_VERSION
from app.utils import setup_logging, ffmpeg_path, resource_path
from app.window import MainWindow


def main():
    setup_logging()
    logging.info('Startup %s %s; yt-dlp %s', APP_NAME, APP_VERSION, yt_dlp.version.__version__)
    logging.info('FFmpeg bundled: %s', resource_path('vendor/ffmpeg/ffmpeg.exe').is_file())
    app = QApplication(sys.argv)
    test_settings = None
    if '--smoke-test' in sys.argv or '--integration-test' in sys.argv:
        test_settings = tempfile.TemporaryDirectory(prefix='media-downloader-test-settings-')
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, test_settings.name)
    app.setApplicationName(APP_NAME)
    app.setStyle('Fusion')
    def exception_handler(kind, value, tb):
        logging.error('Uncaught exception', exc_info=(kind, value, tb))
        QMessageBox.critical(None, APP_NAME, 'An unexpected error occurred. Please restart the app. Details were saved in the application log.')
    sys.excepthook = exception_handler
    window = MainWindow()
    window.show()
    if '--integration-test' in sys.argv:
        from app.smoke import integration
        index = sys.argv.index('--integration-test')
        integration(app, window, *sys.argv[index + 1:index + 4])
    if '--smoke-test' in sys.argv:
        output = Path(sys.argv[sys.argv.index('--smoke-test') + 1])
        def smoke():
            ffmpeg = subprocess.run([str(ffmpeg_path()), '-version'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            report = dict(window_visible=window.isVisible(), ffmpeg_ok=ffmpeg.returncode == 0,
                          ffmpeg_path=str(ffmpeg_path()), frozen=bool(getattr(sys, 'frozen', False)),
                          deno_exists=resource_path('vendor/deno/deno.exe').is_file(), yt_dlp=yt_dlp.version.__version__)
            report['console_window'] = bool(ctypes.windll.kernel32.GetConsoleWindow())
            report['executable'] = sys.executable
            window.grab().save(str(output.with_suffix('.png')))
            output.write_text(json.dumps(report, indent=2), encoding='utf-8')
            app.quit()
        QTimer.singleShot(700, smoke)
    return app.exec()
