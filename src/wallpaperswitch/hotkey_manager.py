import logging
from typing import Optional
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("WallpaperSwitch")

ALT_KEYS = {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
SHIFT_KEYS = {
    keyboard.Key.shift,
    getattr(keyboard.Key, "shift_l", keyboard.Key.shift),
    getattr(keyboard.Key, "shift_r", keyboard.Key.shift),
}


class HotkeyEmitter(QObject):
    triggered = pyqtSignal()


class HotkeyManager:
    """
    Global keyboard listener.
    Supports pure modifier combos like 'alt+shift' as well as standard combos like '<alt>+<shift>+w'.
    """

    def __init__(self, hotkey_str: str = "alt+shift"):
        self.hotkey_str = hotkey_str.strip().lower()
        self.emitter = HotkeyEmitter()

        self._listener: Optional[keyboard.Listener] = None
        self._global_hotkeys: Optional[keyboard.GlobalHotKeys] = None

        self._alt_down = False
        self._shift_down = False
        self._triggered = False

    def start(self):
        """Start listening in background thread."""
        clean_key = self.hotkey_str.replace(" ", "")

        if clean_key in ("alt+shift", "shift+alt"):
            # Stateful modifier tracking for Alt+Shift
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
                logger.warning(f"Failed to bind hotkey {formatted}: {e}. Falling back to Alt+Shift.")
                self._listener = keyboard.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release,
                )
                self._listener.daemon = True
                self._listener.start()

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
