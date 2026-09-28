"""Generate the app's original vector-style icon using Qt (no external artwork)."""
from pathlib import Path
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QPolygonF
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

app = QApplication([])
path = Path(__file__).resolve().parent.parent / 'app/resources'
path.mkdir(parents=True, exist_ok=True)
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QColor('#2862df'))
painter.drawRoundedRect(8, 8, 240, 240, 52, 52)
painter.setBrush(QColor('white'))
painter.drawPolygon(QPolygonF([QPointF(103, 55), QPointF(103, 130), QPointF(72, 130), QPointF(128, 183), QPointF(184, 130), QPointF(153, 130), QPointF(153, 55)]))
painter.setPen(QPen(QColor('white'), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
painter.drawLine(72, 204, 184, 204)
painter.end()
image.save(str(path / 'icon.ico'))
image.save(str(path / 'icon.png'))
