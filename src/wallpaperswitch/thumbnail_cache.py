import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageOps
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtGui import QPixmap, QImage

from wallpaperswitch.config import get_project_root

logger = logging.getLogger("WallpaperSwitch")

CACHE_DIR = get_project_root() / ".cache" / "thumbnails"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Safety limit for decompression bombs (120 Megapixels max)
Image.MAX_IMAGE_PIXELS = 120_000_000


def get_cache_key(file_path: Path, width: int, height: int) -> str:
    """Generate a unique cache filename based on path, mtime, and dimensions."""
    try:
        mtime = file_path.stat().st_mtime
    except Exception:
        mtime = 0
    raw = f"{file_path.resolve()}_{mtime}_{width}x{height}"
    hashed = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{hashed}.png"


def generate_thumbnail_image(file_path: Path, width: int, height: int) -> Optional[Path]:
    """Generate cropped thumbnail safely using Pillow and save to disk cache."""
    cache_file = CACHE_DIR / get_cache_key(file_path, width, height)
    if cache_file.exists():
        return cache_file

    try:
        with Image.open(file_path) as img:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                pass
            else:
                img = img.convert("RGB")

            # High-DPI 2x supersampling for crisp display
            render_w = width * 2
            render_h = height * 2
            thumb = ImageOps.fit(
                img, (render_w, render_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
            )
            thumb.save(cache_file, "PNG", optimize=True)
            return cache_file
    except Image.DecompressionBombError:
        logger.error(f"Image too large to process (decompression bomb protection): {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail for '{file_path}': {e}")
        return None


class ThumbnailSignals(QObject):
    # Pass QImage across thread boundary (QImage is thread-safe, QPixmap is GUI thread only)
    ready = pyqtSignal(str, QImage)


class ThumbnailTask(QRunnable):
    """Runnable task to generate/load a thumbnail safely in threadpool."""

    def __init__(self, file_path: Path, width: int, height: int, signals: ThumbnailSignals):
        super().__init__()
        self.file_path = file_path
        self.width = width
        self.height = height
        self.signals = signals

    def run(self):
        try:
            cache_file = generate_thumbnail_image(self.file_path, self.width, self.height)
            if cache_file and cache_file.exists():
                qimg = QImage(str(cache_file))
                if not qimg.isNull():
                    self.signals.ready.emit(str(self.file_path), qimg)
        except Exception as e:
            logger.error(f"ThumbnailTask error for {self.file_path}: {e}")


class ThumbnailManager(QObject):
    """Manages thread pool and memory cache for smooth thumbnail delivery."""

    thumbnail_loaded = pyqtSignal(str, QPixmap)

    def __init__(self, card_width: int = 140, card_height: int = 230):
        super().__init__()
        self.card_width = card_width
        self.card_height = card_height
        self.thread_pool = QThreadPool.globalInstance()
        self.signals = ThumbnailSignals()
        self.signals.ready.connect(self._on_thumbnail_ready)
        self.memory_cache: Dict[str, QPixmap] = {}

    def _on_thumbnail_ready(self, file_path: str, qimage: QImage):
        # Convert QImage to QPixmap on GUI main thread
        pixmap = QPixmap.fromImage(qimage)
        self.memory_cache[file_path] = pixmap
        self.thumbnail_loaded.emit(file_path, pixmap)

    def get_thumbnail(self, file_path: Path) -> Optional[QPixmap]:
        key = str(file_path)
        if key in self.memory_cache:
            return self.memory_cache[key]

        cache_file = CACHE_DIR / get_cache_key(file_path, self.card_width, self.card_height)
        if cache_file.exists():
            pix = QPixmap(str(cache_file))
            if not pix.isNull():
                self.memory_cache[key] = pix
                return pix

        task = ThumbnailTask(file_path, self.card_width, self.card_height, self.signals)
        self.thread_pool.start(task)
        return None
