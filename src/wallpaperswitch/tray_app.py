import logging
import os
import sys
import winreg
from pathlib import Path

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QFileDialog

from wallpaperswitch.config import load_config, save_config, get_project_root

logger = logging.getLogger("WallpaperSwitch")

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WallpaperSwitch"


def is_run_at_startup() -> bool:
    """Check if app is registered in Windows startup registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return False


def set_run_at_startup(enable: bool) -> bool:
    """Enable or disable Windows startup registry entry safely."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enable:
                script_path = (get_project_root() / "main.py").resolve()
                pythonw = Path(sys.executable).parent / "pythonw.exe"
                if not pythonw.exists():
                    pythonw = Path(sys.executable).resolve()
                cmd = f'"{pythonw}" "{script_path}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                logger.info(f"Registered startup command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Removed startup registry entry")
                except OSError:
                    pass
        return True
    except Exception as e:
        logger.error(f"Error toggling Windows startup: {e}")
        return False


def create_tray_icon() -> QIcon:
    """Generate a sleek, modern desktop/wallpaper vector icon."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(110, 195, 255), 2.2)
    painter.setPen(pen)
    painter.setBrush(QColor(20, 26, 35))
    painter.drawRoundedRect(3, 4, 26, 18, 3, 3)

    painter.setPen(QPen(QColor(110, 195, 255), 2.0))
    painter.drawLine(16, 23, 16, 27)
    painter.drawLine(11, 27, 21, 27)

    inner_pen = QPen(QColor(255, 255, 255, 180), 1.5)
    painter.setPen(inner_pen)
    painter.drawLine(6, 17, 12, 11)
    painter.drawLine(12, 11, 17, 15)
    painter.drawLine(17, 15, 22, 9)
    painter.drawLine(22, 9, 26, 14)

    painter.end()
    return QIcon(pix)


class TrayApp(QObject):
    toggle_requested = pyqtSignal()
    folder_changed = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.tray_icon = QSystemTrayIcon(parent)
        self.tray_icon.setIcon(create_tray_icon())
        self.tray_icon.setToolTip(f"Wallpaper Switcher ({self.config.get('hotkey', 'Alt+Shift').upper()})")

        self._build_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #1e222b;
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2b3547;
                color: #6ec3ff;
            }
            """
        )

        hotkey_display = self.config.get("hotkey", "Alt+Shift").upper()
        act_toggle = menu.addAction(f"Toggle Wallpapers ({hotkey_display})")
        act_toggle.triggered.connect(self.toggle_requested.emit)

        folder = self.config.get("wallpaper_folder", r"D:\Wallpapers")
        act_open_folder = menu.addAction(f"Open Folder ({folder})")
        act_open_folder.triggered.connect(self._open_folder)

        act_choose_folder = menu.addAction("Select Wallpaper Folder...")
        act_choose_folder.triggered.connect(self._choose_folder)

        act_refresh = menu.addAction("Refresh Wallpapers")
        act_refresh.triggered.connect(self.refresh_requested.emit)

        menu.addSeparator()

        act_startup = QAction("Run at Windows Startup", menu)
        act_startup.setCheckable(True)
        act_startup.setChecked(is_run_at_startup())
        act_startup.toggled.connect(self._toggle_startup)
        menu.addAction(act_startup)

        menu.addSeparator()

        act_exit = menu.addAction("Exit")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_requested.emit()

    def _open_folder(self):
        folder = self.config.get("wallpaper_folder", r"D:\Wallpapers")
        try:
            p = Path(folder).resolve()
            if p.is_dir():
                os.startfile(str(p))
            else:
                logger.warning(f"Folder is not a directory: {p}")
        except Exception as e:
            logger.error(f"Failed to open wallpaper folder: {e}")

    def _choose_folder(self):
        current = self.config.get("wallpaper_folder", r"D:\Wallpapers")
        selected = QFileDialog.getExistingDirectory(None, "Select Wallpaper Folder", current)
        if selected:
            selected_path = Path(selected).resolve()
            if selected_path.is_dir():
                self.config["wallpaper_folder"] = str(selected_path)
                save_config(self.config)
                self._build_menu()
                self.folder_changed.emit(str(selected_path))

    def _toggle_startup(self, checked: bool):
        set_run_at_startup(checked)

    def show(self):
        self.tray_icon.show()
