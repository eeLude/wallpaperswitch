import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QRectF,
    QFileSystemWatcher,
    QTimer,
    QEvent,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
    QKeyEvent,
    QMouseEvent,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QCursor,
)
from PyQt6.QtWidgets import (
    QWidget,
    QScrollArea,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
)

from wallpaperswitch.config import load_config
from wallpaperswitch.wallpaper_engine import (
    get_wallpapers,
    get_current_wallpaper,
    apply_wallpaper,
    SUPPORTED_EXTENSIONS,
)
from wallpaperswitch.thumbnail_cache import ThumbnailManager
from wallpaperswitch.ui_cards import WallpaperCardWidget

logger = logging.getLogger("WallpaperSwitch")


class SmoothScrollArea(QScrollArea):
    """Horizontal scroll area with mouse-wheel translation and drag-to-scroll."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent; border: none;")

        self._is_dragging = False
        self._drag_start_x = 0
        self._scroll_start_x = 0

    def wheelEvent(self, event: QWheelEvent):
        """Translate vertical scroll wheel into smooth horizontal scroll."""
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()

        h_bar = self.horizontalScrollBar()
        step = int(-delta * 1.5)
        h_bar.setValue(h_bar.value() + step)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_x = event.globalPosition().toPoint().x()
            self._scroll_start_x = self.horizontalScrollBar().value()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging:
            delta_x = event.globalPosition().toPoint().x() - self._drag_start_x
            self.horizontalScrollBar().setValue(self._scroll_start_x - delta_x)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False
        super().mouseReleaseEvent(event)


class ToastNotification(QWidget):
    """Subtle floating toast for user feedback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(200, 36)
        self._text = "Wallpaper Applied"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self._text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-weight: 600; font-family: 'Segoe UI', sans-serif;"
        )
        layout.addWidget(self.label)

        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 1500):
        self._text = text
        self.label.setText(text)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        painter.fillPath(path, QColor(20, 24, 32, 235))

        pen = QPen(QColor(110, 195, 255, 200), 1.2)
        painter.setPen(pen)
        painter.drawPath(path)


class WallpaperOverlay(QWidget):
    """
    Main floating horizontal wallpaper dock window.
    """

    wallpaper_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.thumbnail_manager = ThumbnailManager(
            card_width=self.config.get("card_width", 140),
            card_height=self.config.get("card_height", 230),
        )
        self.thumbnail_manager.thumbnail_loaded.connect(self._on_thumbnail_ready)

        self.cards: List[WallpaperCardWidget] = []
        self.active_wallpaper_path: Optional[str] = get_current_wallpaper()

        self._init_window_flags()
        self._init_ui()
        self._init_folder_watcher()
        self.setAcceptDrops(True)

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dock_container = QWidget(self)
        self.dock_container.setObjectName("dockContainer")
        self.dock_layout = QVBoxLayout(self.dock_container)
        self.dock_layout.setContentsMargins(8, 8, 8, 8)

        self.scroll_area = SmoothScrollArea(self.dock_container)
        self.cards_content = QWidget()
        self.cards_content.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.scroll_area.setWidget(self.cards_content)
        self.dock_layout.addWidget(self.scroll_area)
        main_layout.addWidget(self.dock_container)

        self.toast = ToastNotification(self)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 8)
        self.dock_container.setGraphicsEffect(shadow)

    def _calculate_dock_size(self):
        """Dynamic dock width that snugly hugs the cards and centers on active monitor."""
        # Multi-monitor awareness: detect screen where cursor is currently located
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else self.screen().geometry()

        card_w = self.config.get("card_width", 140)
        card_h = self.config.get("card_height", 230)
        spacing = 8
        margin_horiz = 16

        num_cards = len(self.cards)
        if num_cards == 0:
            content_w = 460
        else:
            content_w = num_cards * card_w + max(0, num_cards - 1) * spacing + margin_horiz

        max_w = int(screen_geo.width() * 0.92)
        dock_w = min(content_w, max_w)
        dock_h = card_h + 16

        window_w = dock_w + 24
        window_h = dock_h + 24

        self.setFixedSize(window_w, window_h)
        self.dock_container.setFixedSize(dock_w, dock_h)
        self.scroll_area.setFixedHeight(card_h + 2)

        # Center horizontally on the active monitor, lower-middle third
        pos_x = screen_geo.x() + (screen_geo.width() - window_w) // 2
        pos_y = screen_geo.y() + int((screen_geo.height() - window_h) * 0.58)
        self.move(pos_x, pos_y)

        self.toast.move(
            (self.width() - self.toast.width()) // 2,
            (self.height() - self.toast.height()) // 2,
        )

    def paintEvent(self, event):
        """Draw aesthetic frosted glass backdrop."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        c_rect = self.dock_container.geometry()
        r = 16.0
        path = QPainterPath()
        path.addRoundedRect(QRectF(c_rect), r, r)

        painter.fillPath(path, QColor(16, 20, 26, 195))

        pen = QPen(QColor(255, 255, 255, 28), 1.0)
        painter.setPen(pen)
        painter.drawPath(path)

    def _init_folder_watcher(self):
        """Initialize or update folder watcher cleanly."""
        if not hasattr(self, "watcher"):
            self.watcher = QFileSystemWatcher(self)
            self.watcher.directoryChanged.connect(self._on_folder_changed)

        existing_dirs = self.watcher.directories()
        if existing_dirs:
            self.watcher.removePaths(existing_dirs)

        folder = self.config.get("wallpaper_folder", r"D:\Wallpapers")
        folder_path = Path(folder).resolve()
        try:
            if folder_path.is_dir():
                self.watcher.addPath(str(folder_path))
        except Exception as e:
            logger.warning(f"Could not watch directory '{folder}': {e}")

    def _on_folder_changed(self, path):
        QTimer.singleShot(300, self.refresh_wallpapers)

    def refresh_wallpapers(self):
        """Re-scan wallpaper folder and populate cards."""
        folder = self.config.get("wallpaper_folder", r"D:\Wallpapers")
        wallpapers = get_wallpapers(folder)
        self.active_wallpaper_path = get_current_wallpaper()

        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        if not wallpapers:
            self._render_empty_state(folder)
            self._calculate_dock_size()
            return

        card_w = self.config.get("card_width", 140)
        card_h = self.config.get("card_height", 230)
        card_r = self.config.get("card_radius", 12)

        for wp in wallpapers:
            is_active = (
                self.active_wallpaper_path is not None
                and str(wp.resolve()).lower() == str(Path(self.active_wallpaper_path).resolve()).lower()
            )
            card = WallpaperCardWidget(
                file_path=wp,
                width=card_w,
                height=card_h,
                radius=card_r,
                is_active=is_active,
                parent=self.cards_content,
            )
            card.clicked.connect(self._on_card_clicked)
            self.cards_layout.addWidget(card)
            self.cards.append(card)

            pix = self.thumbnail_manager.get_thumbnail(wp)
            if pix:
                card.set_pixmap(pix)

        self._calculate_dock_size()

    def _safe_open_folder(self, folder_str: str):
        """Safely open folder in Explorer, verifying it is a directory."""
        try:
            target = Path(folder_str).resolve()
            if target.is_dir():
                os.startfile(str(target))
            else:
                logger.warning(f"Target is not a valid directory: {target}")
        except Exception as e:
            logger.error(f"Failed to open directory '{folder_str}': {e}")

    def _render_empty_state(self, folder: str):
        """Clean empty state when folder contains no wallpapers."""
        empty_container = QWidget(self.cards_content)
        empty_layout = QVBoxLayout(empty_container)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setContentsMargins(20, 10, 20, 10)
        empty_layout.setSpacing(8)

        label = QLabel(
            f"Folder <b style='color:#6ec3ff'>{folder}</b> is empty<br>"
            "<span style='color:rgba(255,255,255,0.6); font-size:12px;'>"
            "Drag & drop wallpapers here or click to open folder"
            "</span>",
            empty_container,
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: white; font-size: 13px; font-family: 'Segoe UI', sans-serif;")

        btn = QPushButton("Open Folder", empty_container)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(110, 195, 255, 0.22);
                color: #ffffff;
                border: 1px solid rgba(110, 195, 255, 0.5);
                border-radius: 7px;
                padding: 5px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(110, 195, 255, 0.38);
                border-color: #6ec3ff;
            }
            """
        )
        btn.clicked.connect(lambda: self._safe_open_folder(folder))

        empty_layout.addWidget(label)
        empty_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.cards_layout.addWidget(empty_container)

    def _on_thumbnail_ready(self, file_path: str, pixmap):
        for card in self.cards:
            if str(card.file_path) == file_path:
                card.set_pixmap(pixmap)

    def _on_card_clicked(self, file_path: str):
        success = apply_wallpaper(file_path)
        if success:
            self.active_wallpaper_path = str(Path(file_path).resolve())
            for card in self.cards:
                card.set_active(
                    str(card.file_path.resolve()).lower() == self.active_wallpaper_path.lower()
                )

            self.toast.show_message("Wallpaper Applied!")
            self.wallpaper_changed.emit(file_path)

            if self.config.get("close_on_select", True):
                QTimer.singleShot(350, self.hide)

    def toggle_visibility(self):
        """Toggle dock open or closed."""
        if self.isVisible():
            self.hide()
        else:
            self.show_dock()

    def show_dock(self):
        """Show and center dock with fresh wallpapers."""
        self.refresh_wallpapers()
        self.show()
        self.raise_()
        self.activateWindow()

    def changeEvent(self, event: QEvent):
        """Dismiss dock when user clicks away or window loses focus."""
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow() and self.isVisible():
                self.hide()
        super().changeEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            bar = self.scroll_area.horizontalScrollBar()
            bar.setValue(bar.value() + 148)
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            bar = self.scroll_area.horizontalScrollBar()
            bar.setValue(bar.value() - 148)
            event.accept()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Support safely dropping images onto the dock to add to wallpaper folder."""
        try:
            folder = Path(self.config.get("wallpaper_folder", r"D:\Wallpapers")).resolve()
            folder.mkdir(parents=True, exist_ok=True)

            added = 0
            for url in event.mimeData().urls():
                local_path = Path(url.toLocalFile()).resolve()
                if local_path.is_file() and local_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    safe_filename = Path(local_path.name).name
                    dest_path = folder / safe_filename

                    if folder not in dest_path.resolve().parents and dest_path.resolve() != folder:
                        logger.warning(f"Prevented illegal path escape: {dest_path}")
                        continue

                    counter = 1
                    stem = dest_path.stem
                    suffix = dest_path.suffix
                    while dest_path.exists():
                        dest_path = folder / f"{stem}_{counter}{suffix}"
                        counter += 1

                    shutil.copy2(local_path, dest_path)
                    added += 1

            if added > 0:
                self.toast.show_message(f"Added {added} wallpaper{'s' if added > 1 else ''}!")
                self.refresh_wallpapers()
        except Exception as e:
            logger.error(f"Error handling dropped files: {e}")

        event.acceptProposedAction()
