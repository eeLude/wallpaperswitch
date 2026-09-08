import ctypes
import logging
import os
import winreg
from pathlib import Path
from typing import List, Optional
from PIL import Image

from wallpaperswitch.config import get_project_root

logger = logging.getLogger("WallpaperSwitch")

SPI_SETDESKWALLPAPER = 0x0014
SPI_GETDESKWALLPAPER = 0x0073
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def get_wallpapers(folder_path: str) -> List[Path]:
    """Scan folder for supported wallpaper image files safely."""
    try:
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            return []

        images: List[Path] = []
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                images.append(entry)

        images.sort(key=lambda p: p.name.lower())
        return images
    except Exception as e:
        logger.error(f"Error scanning wallpaper folder '{folder_path}': {e}")
        return []


def get_current_wallpaper() -> Optional[str]:
    """Retrieve current Windows desktop wallpaper path from registry or API."""
    try:
        buf = ctypes.create_unicode_buffer(512)
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 512, buf, 0):
            val = buf.value
            if val and os.path.exists(val):
                return str(Path(val).resolve())
    except Exception as e:
        logger.debug(f"Failed to query wallpaper via SystemParametersInfoW: {e}")

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ
        ) as key:
            val, _ = winreg.QueryValueEx(key, "WallPaper")
            if val and os.path.exists(val):
                return str(Path(val).resolve())
    except Exception as e:
        logger.debug(f"Failed to query wallpaper via Registry: {e}")

    return None


def set_wallpaper_style_fill() -> None:
    """Set Windows wallpaper style to 'Fill' (Style 10, Tile 0)."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
    except Exception as e:
        logger.warning(f"Could not update WallpaperStyle in registry: {e}")


def apply_wallpaper(image_path: str, cache_dir: Optional[Path] = None) -> bool:
    """
    Set Windows desktop wallpaper to the given image path safely.
    Converts .webp or unsupported formats to a cached PNG if necessary.
    """
    try:
        src_path = Path(image_path).resolve()
        if not src_path.exists() or not src_path.is_file():
            logger.error(f"Wallpaper file does not exist: {src_path}")
            return False

        target_path = src_path

        # If it's a webp, convert it to a cached PNG for Windows compatibility
        if src_path.suffix.lower() == ".webp":
            if cache_dir is None:
                cache_dir = get_project_root() / ".cache" / "converted"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_converted = cache_dir / f"{src_path.stem}_{int(src_path.stat().st_mtime)}.png"

            if not cached_converted.exists():
                with Image.open(src_path) as img:
                    img.save(cached_converted, "PNG")
            target_path = cached_converted

        set_wallpaper_style_fill()

        res = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            str(target_path),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        return bool(res)
    except Exception as e:
        logger.error(f"Failed to apply wallpaper '{image_path}': {e}")
        return False
