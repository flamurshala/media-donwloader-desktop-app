from pathlib import Path

import yt_dlp.version
from PySide6.QtCore import QSettings, QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                              QLineEdit, QPushButton, QComboBox, QCheckBox, QProgressBar,
                              QFileDialog, QMessageBox, QFrame, QListWidget)

from app.config import APP_NAME, APP_ID, APP_VERSION
from app.utils import duration, size, valid_url, resource_path
from app.worker import Worker


STYLE = '''
QMainWindow, QWidget#root { background: #f4f6fa; color: #17233b; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; }
QLabel { color: #17233b; background: transparent; }
QLabel#heading { font-size: 25px; font-weight: 700; }
QLabel#muted { color: #69768b; }
QLabel#videoTitle { font-size: 18px; font-weight: 600; }
QLabel#eyebrow { color: #687b99; font-size: 11px; font-weight: 700; }
QFrame#card { background: white; border: 1px solid #e1e6ef; border-radius: 12px; }
QListWidget { background: white; color: #17233b; border: 1px solid #ccd5e3; border-radius: 6px; padding: 6px; }
QListWidget::item { padding: 3px; }
QLineEdit, QComboBox { background: white; border: 1px solid #ccd5e3; border-radius: 6px; padding: 9px; color: #17233b; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #376de8; }
QComboBox { combobox-popup: 0; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #17233b; border: 1px solid #ccd5e3; outline: 0; selection-background-color: #2862df; selection-color: #ffffff; }
QComboBox QAbstractItemView::item { min-height: 30px; padding: 4px 10px; }
QComboBox QAbstractItemView::item:hover { background-color: #edf3ff; color: #17233b; }
QComboBox QAbstractItemView::item:selected { background-color: #2862df; color: #ffffff; }
QPushButton { background: white; color: #243654; border: 1px solid #ccd5e3; border-radius: 6px; padding: 9px 19px; font-weight: 600; }
QPushButton:hover { background: #edf3ff; border-color: #97b4f7; }
QPushButton#primary { background: #2862df; border-color: #2862df; color: white; }
QPushButton#primary:hover { background: #1c50c4; }
QPushButton#primary:disabled { background: #dbe4f5; border-color: #dbe4f5; color: #8b9bb8; }
QPushButton:disabled { background: #e9edf4; color: #94a0b3; border-color: #e1e6ef; }
QLineEdit:disabled, QComboBox:disabled { background: #f3f5f8; color: #94a0b3; }
QProgressBar { border: none; border-radius: 5px; background: #e7edf7; height: 10px; text-align: center; }
QProgressBar::chunk { background: #3271eb; border-radius: 5px; }
QCheckBox { spacing: 8px; color: #465873; }
QStatusBar { color: #65748b; background: #f4f6fa; }
'''


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(APP_ID, APP_ID)
        self.worker = None
        self.info = None
        self.fetched_url = None
        self.closing = False
        self.last_folder = None
        self.playlist_completed = 0
        self.current_item_text = ""
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path('app/resources/icon.ico'))))
        self.resize(950, 850)
        self.setMinimumSize(760, 710)
        self.setStyleSheet(STYLE)
        root = QWidget(objectName='root')
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 16, 28, 18)
        layout.setSpacing(10)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(label(APP_NAME, 'heading'))
        heading.addWidget(label('Your media. The quality you choose.', 'muted'))
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(label(f'DESKTOP  /  {APP_VERSION}', 'eyebrow'))
        layout.addLayout(header)
        layout.addWidget(label('VIDEO OR PLAYLIST LINK', 'eyebrow'))
        row = QHBoxLayout()
        self.url = QLineEdit(placeholderText='Paste a video or YouTube playlist link here…')
        self.url.setAccessibleName('Video URL')
        self.fetch_button = QPushButton('Fetch', objectName='primary')
        row.addWidget(self.url, 1)
        row.addWidget(self.fetch_button)
        layout.addLayout(row)
        card = QFrame(objectName='card')
        card.setMinimumHeight(143)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(20)
        self.thumbnail = label('▶')
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFixedSize(190, 107)
        self.thumbnail.setStyleSheet('background: #edf2fb; color: #7f9bce; border-radius: 8px; font-size: 32px;')
        card_layout.addWidget(self.thumbnail)
        details = QVBoxLayout()
        details.addWidget(label('MEDIA PREVIEW', 'eyebrow'))
        self.title = label('Start with a video link', 'videoTitle')
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(54)
        details.addWidget(self.title)
        self.creator = label('Fetch a video to see its available qualities.', 'muted')
        self.creator.setWordWrap(True)
        details.addWidget(self.creator)
        self.length = label('—', 'muted')
        details.addWidget(self.length)
        details.addStretch()
        card_layout.addLayout(details, 1)
        layout.addWidget(card)

        self.playlist_list = QListWidget()
        self.playlist_list.setAccessibleName('Playlist contents')
        self.playlist_list.setMaximumHeight(130)
        self.playlist_list.hide()
        layout.addWidget(self.playlist_list)
        self.overall_label = label('Playlist progress')
        self.overall_label.setWordWrap(True)
        self.overall_label.setMaximumHeight(42)
        self.overall = QProgressBar()
        self.overall.setRange(0, 100)
        self.overall.setValue(0)
        self.overall_label.hide()
        self.overall.hide()
        layout.addWidget(self.overall_label)
        layout.addWidget(self.overall)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        self.mode = QComboBox()
        self.mode.addItems(['Video + Audio', 'Video Only', 'Audio Only', 'Separate Video + Audio'])
        self.mode.setCurrentText(self.settings.value('mode', 'Video + Audio'))
        self.quality = QComboBox()
        self.quality.addItem('Best available', None)
        self.format = QComboBox()
        self.format_label = label('OUTPUT FORMAT', 'eyebrow')
        for column, (caption, widget) in enumerate([(label('DOWNLOAD TYPE', 'eyebrow'), self.mode), (label('QUALITY', 'eyebrow'), self.quality), (self.format_label, self.format)]):
            grid.addWidget(caption, 0, column)
            grid.addWidget(widget, 1, column)
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)
        self.compatible = QCheckBox('Prefer MP4 / H.264 compatibility')
        self.compatible.setChecked(self.settings.value('compatible', True, type=bool))
        layout.addWidget(self.compatible)
        self.hint = label('', 'muted')
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addWidget(label('SAVE TO', 'eyebrow'))
        row = QHBoxLayout()
        self.directory = QLineEdit(self.settings.value('directory', QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)))
        self.browse = QPushButton('Browse…')
        row.addWidget(self.directory, 1)
        row.addWidget(self.browse)
        layout.addLayout(row)
        layout.addStretch(1)
        progress_header = QHBoxLayout()
        self.status = label('Ready when you are')
        self.status.setWordWrap(True)
        progress_header.addWidget(self.status, 1)
        self.percent = label('—', 'muted')
        progress_header.addWidget(self.percent)
        layout.addLayout(progress_header)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)
        self.stats = label('Size —     •     Speed —     •     ETA —', 'muted')
        layout.addWidget(self.stats)
        actions = QHBoxLayout()
        self.open_folder = QPushButton('Open folder')
        self.open_folder.setEnabled(False)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        self.download_button = QPushButton('Download', objectName='primary')
        self.download_button.setEnabled(False)
        actions.addWidget(self.open_folder)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.download_button)
        layout.addLayout(actions)
        footer = label('Download only content you own or have permission to save.', 'muted')
        layout.addWidget(footer)
        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction('Open download folder', self.show_folder)
        file_menu.addAction('Exit', self.close)
        self.menuBar().addMenu('&Help').addAction('About', self.about)
        self.fetch_button.clicked.connect(self.fetch)
        self.url.returnPressed.connect(self.fetch)
        self.url.textChanged.connect(self.invalidate)
        self.mode.currentTextChanged.connect(self.mode_changed)
        self.format.currentTextChanged.connect(self.format_changed)
        self.browse.clicked.connect(self.choose_folder)
        self.download_button.clicked.connect(self.download)
        self.cancel_button.clicked.connect(self.cancel)
        self.open_folder.clicked.connect(self.show_folder)
        self.mode_changed()
        self.url.setFocus()

    def mode_changed(self):
        mode = self.mode.currentText()
        self.format.blockSignals(True)
        self.format.clear()
        self.format.addItems(['Original', 'MP3', 'M4A', 'WAV', 'FLAC'] if mode == 'Audio Only' else ['MP4', 'MKV', 'WebM'] if mode == 'Video + Audio' else ['Original'])
        self.format.setCurrentText(self.settings.value('format/' + mode, self.format.itemText(0)))
        self.format.blockSignals(False)
        self.format_label.setText('AUDIO FORMAT' if mode == 'Audio Only' else 'OUTPUT FORMAT')
        self.quality.setEnabled(mode != 'Audio Only' and self.worker is None)
        self.format.setEnabled(mode in ('Audio Only', 'Video + Audio') and self.worker is None)
        self.hint.setText({'Video + Audio': 'One finished file. Streams are merged without re-encoding video.', 'Video Only': 'One silent video file. Original video quality is preserved.', 'Audio Only': 'Original preserves the source audio. Converting compressed audio does not restore lost quality.', 'Separate Video + Audio': 'Two files: a silent video and a separate audio track.'}[mode])
        self.format_changed()

    def format_changed(self):
        self.compatible.setEnabled(self.worker is None and self.mode.currentText() == 'Video + Audio' and self.format.currentText() == 'MP4')
        if self.format.currentText():
            self.settings.setValue('format/' + self.mode.currentText(), self.format.currentText())

    def invalidate(self):
        if self.url.text().strip() != self.fetched_url:
            self.info = None
            self.playlist_list.hide()
            self.overall.hide()
            self.overall_label.hide()
            self.download_button.setText('Download')
            self.download_button.setEnabled(False)

    def save_settings(self):
        self.settings.setValue('directory', self.directory.text().strip())
        self.settings.setValue('mode', self.mode.currentText())
        self.settings.setValue('compatible', self.compatible.isChecked())

    def set_busy(self, busy):
        for widget in (self.url, self.fetch_button, self.mode, self.directory, self.browse):
            widget.setEnabled(not busy)
        self.quality.setEnabled(not busy and self.mode.currentText() != 'Audio Only')
        self.format.setEnabled(not busy and self.mode.currentText() in ('Audio Only', 'Video + Audio'))
        self.compatible.setEnabled(not busy and self.mode.currentText() == 'Video + Audio' and self.format.currentText() == 'MP4')
        self.download_button.setEnabled(not busy and self.info is not None)
        self.cancel_button.setEnabled(busy)

    def start(self, kind, payload):
        if self.worker:
            return
        self.current_item_text = ''
        self.worker = Worker(kind, payload)
        self.worker.event.connect(self.on_event)
        self.worker.finished.connect(self.worker_finished)
        self.set_busy(True)
        self.progress.setRange(0, 0)
        self.percent.setText('—')
        self.stats.setText('Size —     •     Speed —     •     ETA —')
        self.status.setText('Fetching video information…' if kind == 'fetch' else 'Preparing download…')
        self.worker.start()

    def fetch(self):
        if self.worker:
            return
        try:
            url = valid_url(self.url.text())
        except ValueError as exc:
            QMessageBox.warning(self, 'Check the link', str(exc))
            return
        self.url.setText(url)
        self.info = None
        self.fetched_url = url
        self.start('fetch', {'url': url})

    def download(self):
        if not self.info or self.worker:
            return
        directory = self.directory.text().strip()
        if not directory or not Path(directory).is_absolute():
            QMessageBox.warning(self, 'Choose a folder', 'Choose a valid, absolute output folder.')
            return
        playlist = self.info if self.info.get('is_playlist') else None
        if playlist and len(playlist['entries']) > 100:
            dialog = QMessageBox(self)
            dialog.setWindowTitle('Large playlist')
            dialog.setText(f"This playlist contains {len(playlist['entries'])} videos. Downloading it may take a long time and use significant disk space.")
            accept = dialog.addButton('Download Playlist', QMessageBox.ButtonRole.AcceptRole)
            dialog.addButton(QMessageBox.StandardButton.Cancel)
            dialog.exec()
            if dialog.clickedButton() != accept:
                return
        self.playlist_completed = 0
        self.overall.setValue(0)
        self.current_item_text = ''
        self.save_settings()
        self.start('download', dict(url=self.fetched_url, directory=directory, playlist=playlist, mode=self.mode.currentText(),
                                   format=self.format.currentText(), height=self.quality.currentData(), compatible=self.compatible.isChecked()))

    def on_event(self, event, value):
        if event == 'current_item':
            self.current_item_text = f"{value['position']} of {value['total']} — {value['title']}"
            self.overall_label.setText('Current video: ' + self.current_item_text)
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.percent.setText('0%')
            self.stats.setText('Size —     •     Speed —     •     ETA —')
        elif event == 'overall':
            self.playlist_completed = value['downloaded'] + value['skipped']
            self.overall.setValue(value['percent'])
            self.overall_label.setText(f"Playlist: {value['downloaded']} downloaded, {value['skipped']} skipped, {value['failed']} failed / {value['total']}")
        elif event == 'playlist_finished':
            self.playlist_summary(value)
        elif event == 'status':
            self.status.setText(value + (' ' + self.current_item_text if self.current_item_text else ''))
            self.progress.setRange(0, 0)
            self.percent.setText('—')
        elif event == 'processing':
            self.progress.setRange(0, 0)
            self.percent.setText('—')
            self.status.setText(value + (' ' + self.current_item_text if self.current_item_text else ''))
            self.stats.setText('Finishing your files…')
            if value == 'Saving completed files…':
                self.cancel_button.setEnabled(False)
        elif event == 'progress':
            total = value.get('total_bytes') or value.get('total_bytes_estimate')
            done = value.get('downloaded_bytes') or 0
            if total:
                self.progress.setRange(0, 100)
                percent = min(100, int(done / total * 100))
                self.progress.setValue(percent)
                self.percent.setText(f'{percent}% of current stream')
            estimate = '~' if not value.get('total_bytes') and total else ''
            self.stats.setText(f"{size(done)} / {estimate}{size(total)}     •     {size(value.get('speed'))}/s     •     ETA {duration(value.get('eta'))}")
        elif event == 'result':
            self.progress.setRange(0, 100)
            if self.worker.kind == 'fetch':
                self.info = value
                self.title.setText(value['title'][:220])
                self.title.setToolTip(value['title'])
                self.creator.setText(value['uploader'][:160])
                playlist = value.get('is_playlist', False)
                self.length.setText(f"Playlist • {len(value['entries'])} video{'s' if len(value['entries']) != 1 else ''}" if playlist else duration(value['duration']))
                self.download_button.setText('Download Playlist' if playlist else 'Download')
                self.playlist_list.clear()
                if playlist:
                    self.playlist_list.addItems([f"{entry['index']}. {entry['title']}" for entry in value['entries']])
                self.playlist_list.setVisible(playlist)
                self.overall.setVisible(playlist)
                self.overall_label.setVisible(playlist)
                self.overall.setValue(0)
                self.overall_label.setText('Playlist progress')
                self.quality.clear()
                self.quality.addItem('Best available', None)
                for height in value['qualities']:
                    self.quality.addItem(f'{height}p', height)
                pixmap = QPixmap()
                if value['thumbnail'] and pixmap.loadFromData(value['thumbnail']):
                    self.thumbnail.setPixmap(pixmap.scaled(self.thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.thumbnail.setText('▶')
                self.progress.setValue(0)
                self.status.setText('Media information loaded. Choose your download options.')
            else:
                self.progress.setValue(100)
                self.percent.setText('Complete')
                self.last_folder = self.worker.payload['directory']
                self.open_folder.setEnabled(True)
                self.status.setText('Download completed successfully.')
                names = ', '.join(Path(p).name for p in value['files'])
                self.stats.setText(names[:110])
                self.stats.setToolTip(names)
                if value['notes']:
                    QMessageBox.information(self, 'Download completed', '\n\n'.join(value['notes']))
        elif event in ('error', 'cancelled'):
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.percent.setText('—')
            self.status.setText('Download cancelled.' if event == 'cancelled' else 'Unable to complete the operation.')
            if event == 'error':
                QMessageBox.warning(self, 'Operation failed', value)

    def playlist_summary(self, value):
        self.last_folder = value['folder']
        self.open_folder.setEnabled(Path(self.last_folder).is_dir())
        state = 'cancelled' if value['cancelled'] else 'stopped' if value['error'] else 'completed'
        self.status.setText(f'Playlist download {state}.')
        self.progress.setRange(0, 100)
        self.progress.setValue(0 if state != 'completed' else 100)
        self.percent.setText(state.capitalize())
        self.stats.setText(f"Downloaded: {value['downloaded']} • Skipped: {value['skipped']} • Failed: {value['failed']} • Total: {value['total']}")
        if self.closing:
            return
        dialog = QMessageBox(self)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.setWindowTitle(f'Playlist download {state}')
        dialog.setText(f"{value['title']}\n\n{self.stats.text()}\n\nSaved to:\n{value['folder']}" + (f"\n\n{value['error']}" if value['error'] else ''))
        if value['details']:
            dialog.setDetailedText('\n'.join(value['details']))
        open_button = dialog.addButton('Open Folder', QMessageBox.ButtonRole.ActionRole)
        dialog.addButton(QMessageBox.StandardButton.Close)
        dialog.exec()
        if dialog.clickedButton() == open_button:
            self.show_folder()

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)
        if self.closing:
            self.close()

    def cancel(self):
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText('Cancelling…')

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Save downloads to', self.directory.text())
        if path:
            self.directory.setText(path)
            self.save_settings()

    def show_folder(self):
        path = self.last_folder or self.directory.text()
        if Path(path).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def about(self):
        QMessageBox.about(self, f'About {APP_NAME}', f'{APP_NAME} {APP_VERSION}\n\nyt-dlp {yt_dlp.version.__version__}\nNative desktop video and audio downloader.\n\nFFmpeg, Qt / PySide6, Deno and yt-dlp notices are included in LICENSES.md and the licenses folder.\n\nUse only for content you are permitted to download.')

    def closeEvent(self, event):
        if self.worker:
            if not self.closing:
                dialog = QMessageBox(self)
                dialog.setWindowTitle('Operation in progress')
                dialog.setText(f"A playlist download is in progress. {self.playlist_completed} of {len(self.worker.payload['playlist']['entries'])} videos completed or skipped. Cancel the playlist and exit?" if self.worker.payload.get('playlist') else 'A download or fetch is currently in progress. Cancel it and exit?')
                quit_button = dialog.addButton('Cancel Download and Exit', QMessageBox.ButtonRole.DestructiveRole)
                dialog.addButton('Keep Downloading', QMessageBox.ButtonRole.RejectRole)
                dialog.exec()
                if dialog.clickedButton() == quit_button:
                    self.closing = True
                    self.cancel()
            event.ignore()
        else:
            self.save_settings()
            event.accept()
