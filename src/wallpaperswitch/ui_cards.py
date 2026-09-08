from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QPixmap,
    QLinearGradient,
)
from PyQt6.QtWidgets import QWidget


class WallpaperCardWidget(QWidget):
    """
    Vertical wallpaper card with rounded corners, subtle border,
    hover elevation, and click-to-apply action.
    """

    clicked = pyqtSignal(str)

    def __init__(
        self,
        file_path: Path,
        width: int = 140,
        height: int = 230,
        radius: int = 12,
        is_active: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.file_path = file_path
        self.card_width = width
        self.card_height = height
        self.card_radius = radius
        self.is_active = is_active
        self.pixmap: Optional[QPixmap] = None
        self._hover_progress = 0.0

        self.setFixedSize(self.card_width, self.card_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(file_path.stem)

        self.anim = QPropertyAnimation(self, b"hover_progress")
        self.anim.setDuration(160)

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, val: float):
        self._hover_progress = val
        self.update()

    hover_progress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def set_pixmap(self, pixmap: QPixmap):
        self.pixmap = pixmap
        self.update()

    def set_active(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self.update()

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._hover_progress)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._hover_progress)
        self.anim.setEndValue(0.0)
        self.anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(str(self.file_path))
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )

        # Hover elevation: lift slightly (4px) when hovered
        lift = 4.0 * self._hover_progress
        rect = QRectF(0, 4.0 - lift, self.card_width, self.card_height - 4.0)
        r = float(self.card_radius)

        path = QPainterPath()
        path.addRoundedRect(rect, r, r)

        painter.save()
        painter.setClipPath(path)

        if self.pixmap and not self.pixmap.isNull():
            painter.drawPixmap(rect.toRect(), self.pixmap)
        else:
            grad = QLinearGradient(0, 0, 0, self.card_height)
            grad.setColorAt(0.0, QColor(32, 35, 42))
            grad.setColorAt(1.0, QColor(18, 20, 25))
            painter.fillRect(rect, grad)

        # Subtle dark gradient at the bottom for depth
        bottom_grad = QLinearGradient(0, rect.top() + rect.height() * 0.70, 0, rect.bottom())
        bottom_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        bottom_grad.setColorAt(1.0, QColor(0, 0, 0, 110))
        painter.fillRect(rect, bottom_grad)

        if self._hover_progress > 0:
            sheen = QColor(255, 255, 255, int(18 * self._hover_progress))
            painter.fillRect(rect, sheen)

        painter.restore()

        # Draw crisp, delicate border
        pen_width = 1.0
        if self.is_active:
            border_col = QColor(110, 195, 255, 240)
            pen_width = 2.0
        else:
            base_alpha = int(55 + 160 * self._hover_progress)
            border_col = QColor(255, 255, 255, base_alpha)

        pen = QPen(border_col, pen_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        half_pen = pen_width / 2.0
        border_rect = rect.adjusted(half_pen, half_pen, -half_pen, -half_pen)
        border_path = QPainterPath()
        border_path.addRoundedRect(border_rect, r - half_pen, r - half_pen)
        painter.drawPath(border_path)

        # If active desktop wallpaper, draw checkmark badge
        if self.is_active:
            dot_w = 20
            dot_h = 20
            dot_x = (self.card_width - dot_w) / 2
            dot_y = rect.bottom() - 26
            dot_rect = QRectF(dot_x, dot_y, dot_w, dot_h)

            painter.setBrush(QColor(110, 195, 255, 240))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_rect)

            painter.setPen(QPen(QColor(10, 14, 20), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            cx, cy = dot_rect.center().x(), dot_rect.center().y()
            painter.drawLine(int(cx - 4), int(cy), int(cx - 1), int(cy + 3))
            painter.drawLine(int(cx - 1), int(cy + 3), int(cx + 4), int(cy - 3))
