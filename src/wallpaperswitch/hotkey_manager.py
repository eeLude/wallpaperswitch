import logging
import time
from typing import Optional
from pynput import keyboard, mouse
from PyQt6.QtCore import QObject, pyqtSignal

from wallpaperswitch.desktop_detector import is_empty_desktop, get_system_double_click_time

logger = logging.getLogger("WallpaperSwitch")

ALT_KEYS = {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
SHIFT_KEYS = {
    keyboard.Key.shift,
    getattr(keyboard.Key, "shift_l", keyboard.Key.shift),
    getattr(keyboard.Key, "shift_r", keyboard.Key.shift),
}


class HotkeyEmitter(QObject):
    triggered = pyqtSignal()


class DesktopMouseListener:
    """
    Listens for double-clicks on empty desktop wallpaper space.
    Completely ignores clicks inside games, open applications, or desktop icons.
    """

    def __init__(self, callback):
        self.callback = callback
        self.last_click_time = 0.0
        self.last_click_pos = (0, 0)
        self.double_click_threshold = get_system_double_click_time()
        self._listener: Optional[mouse.Listener] = None

    def start(self):
        """Start global mouse listener in background thread."""
        try:
            self._listener = mouse.Listener(on_click=self._on_click)
            self._listener.daemon = True
            self._listener.start()
            logger.info("Desktop double-click listener active")
        except Exception as e:
            logger.error(f"Failed to start desktop mouse listener: {e}")

    def _on_click(self, x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            now = time.time()
            dt = now - self.last_click_time
            dx = abs(x - self.last_click_pos[0])
            dy = abs(y - self.last_click_pos[1])
            self.last_click_time = now
            self.last_click_pos = (x, y)

            if dt <= self.double_click_threshold and dx <= 6 and dy <= 6:
                # Reset so triple-click doesn't double-fire
                self.last_click_time = 0.0
                if is_empty_desktop(x, y):
                    logger.debug("Desktop double-click detected on empty wallpaper space")
                    self.callback()

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception as e:
                logger.debug(f"Error stopping desktop mouse listener: {e}")
            self._listener = None


class HotkeyManager:
    """
    Global input manager supporting both desktop double-click and keyboard hotkeys.
    """

    def __init__(
        self,
        hotkey_str: str = "alt+shift+w",
        enable_hotkey: bool = True,
        enable_double_click: bool = True,
    ):
        self.hotkey_str = hotkey_str.strip().lower()
        self.enable_hotkey = enable_hotkey
        self.enable_double_click = enable_double_click
        self.emitter = HotkeyEmitter()

        self._listener: Optional[keyboard.Listener] = None
        self._global_hotkeys: Optional[keyboard.GlobalHotKeys] = None
        self._mouse_listener: Optional[DesktopMouseListener] = None

        self._alt_down = False
        self._shift_down = False
        self._triggered = False

    def start(self):
        """Start configured listeners in background threads."""
        if self.enable_double_click:
            self._mouse_listener = DesktopMouseListener(self._on_triggered)
            self._mouse_listener.start()

        if self.enable_hotkey and self.hotkey_str:
            clean_key = self.hotkey_str.replace(" ", "")
            if clean_key in ("alt+shift", "shift+alt"):
                self._listener = keyboard.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release,
                )
                self._listener.daemon = True
                self._listener.start()
                logger.info("Hotkey listener active for Alt+Shift")
            else:
                formatted = self._format_for_pynput(clean_key)
                try:
                    self._global_hotkeys = keyboard.GlobalHotKeys(
                        {formatted: self._on_triggered}
                    )
                    self._global_hotkeys.daemon = True
                    self._global_hotkeys.start()
                    logger.info(f"Hotkey listener active for {formatted}")
                except Exception as e:
                    logger.warning(f"Failed to bind hotkey {formatted}: {e}")

    def _format_for_pynput(self, key_str: str) -> str:
        parts = key_str.split("+")
        formatted_parts = []
        for p in parts:
            if p in ("alt", "shift", "ctrl", "cmd", "super"):
                formatted_parts.append(f"<{p}>")
            else:
                formatted_parts.append(p)
        return "+".join(formatted_parts)

    def _on_press(self, key):
        if key in ALT_KEYS:
            self._alt_down = True
        elif key in SHIFT_KEYS:
            self._shift_down = True

        if self._alt_down and self._shift_down and not self._triggered:
            self._triggered = True
            self._on_triggered()

    def _on_release(self, key):
        if key in ALT_KEYS:
            self._alt_down = False
        if key in SHIFT_KEYS:
            self._shift_down = False

        if not self._alt_down or not self._shift_down:
            self._triggered = False

    def _on_triggered(self):
        self.emitter.triggered.emit()

    def stop(self):
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

        if self._listener:
            try:
                self._listener.stop()
            except Exception as e:
                logger.debug(f"Error stopping keyboard listener: {e}")
            self._listener = None

        if self._global_hotkeys:
            try:
                self._global_hotkeys.stop()
            except Exception as e:
                logger.debug(f"Error stopping global hotkeys: {e}")
            self._global_hotkeys = None
