import ctypes
import logging
import signal
import sys
from PyQt6.QtWidgets import QApplication

from wallpaperswitch.config import load_config
from wallpaperswitch.ui_overlay import WallpaperOverlay
from wallpaperswitch.tray_app import TrayApp
from wallpaperswitch.hotkey_manager import HotkeyManager

logger = logging.getLogger("WallpaperSwitch")

MUTEX_NAME = "Local\\WallpaperSwitch_SingleInstance_Mutex"
ERROR_ALREADY_EXISTS = 183


def ensure_single_instance():
    """Ensure only one instance of the application runs at a time using a Win32 Mutex."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == ERROR_ALREADY_EXISTS:
        logger.warning("Another instance of WallpaperSwitch is already running. Exiting.")
        sys.exit(0)
    return mutex


def run_app():
    # Enforce single instance
    mutex = ensure_single_instance()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("WallpaperSwitch")
    app.setApplicationDisplayName("Wallpaper Switcher")
    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    overlay = WallpaperOverlay()

    tray = TrayApp()
    tray.show()

    tray.toggle_requested.connect(overlay.toggle_visibility)
    tray.refresh_requested.connect(overlay.refresh_wallpapers)

    def on_folder_changed(new_folder):
        logger.info(f"Wallpaper folder switched to: {new_folder}")
        overlay.config = load_config()
        overlay._init_folder_watcher()
        overlay.refresh_wallpapers()

    tray.folder_changed.connect(on_folder_changed)

    hotkey = config.get("hotkey", "alt+shift")
    hotkey_mgr = HotkeyManager(hotkey)
    hotkey_mgr.emitter.triggered.connect(overlay.toggle_visibility)
    hotkey_mgr.start()

    def on_exit():
        logger.info("Exiting WallpaperSwitch...")
        hotkey_mgr.stop()
        overlay.close()
        app.quit()

    tray.exit_requested.connect(on_exit)

    # Initially display dock so user immediately sees it
    overlay.show_dock()

    exit_code = app.exec()

    # Release Win32 mutex handle on clean exit
    if mutex:
        ctypes.windll.kernel32.CloseHandle(mutex)

    sys.exit(exit_code)
