import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("WallpaperSwitch")

user32 = ctypes.windll.user32


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class LVHITTESTINFO(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("flags", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
    ]


user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL

LRESULT = ctypes.c_ssize_t
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.c_void_p]
user32.SendMessageW.restype = LRESULT

user32.GetDoubleClickTime.restype = wintypes.UINT

LVM_HITTEST = 0x1012


def get_system_double_click_time() -> float:
    """Return the system double-click threshold in seconds."""
    try:
        ms = user32.GetDoubleClickTime()
        return max(0.2, min(float(ms) / 1000.0, 1.0))
    except Exception:
        return 0.5


def get_class_name(hwnd: int) -> str:
    """Return the Win32 window class name for given HWND."""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_empty_desktop(x: int, y: int) -> bool:
    """
    Check if screen coordinates (x, y) are over empty desktop wallpaper space.
    Returns False if over another application window, taskbar, or desktop icon.
    """
    try:
        pt = POINT(int(x), int(y))
        hwnd = user32.WindowFromPoint(pt)
        if not hwnd:
            return False

        cls = get_class_name(hwnd)

        # Direct desktop wallpaper containers (WorkerW or Progman)
        if cls in ("WorkerW", "Progman", "SHELLDLL_DefView"):
            return True

        # Desktop icon listview (SysListView32)
        if cls == "SysListView32":
            parent = user32.GetParent(hwnd)
            parent_cls = get_class_name(parent) if parent else ""
            if parent_cls in ("SHELLDLL_DefView", "Progman", "WorkerW"):
                # Hit-test listview to verify cursor is NOT over an icon
                pt_client = POINT(int(x), int(y))
                if user32.ScreenToClient(hwnd, ctypes.byref(pt_client)):
                    info = LVHITTESTINFO()
                    info.pt = pt_client
                    res = user32.SendMessageW(hwnd, LVM_HITTEST, 0, ctypes.byref(info))
                    # If iItem == -1, no icon was clicked (empty space)
                    return info.iItem == -1
                return True

        return False
    except Exception as e:
        logger.debug(f"Error checking desktop window under cursor: {e}")
        return False
