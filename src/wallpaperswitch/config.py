import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("WallpaperSwitch")

DEFAULT_CONFIG: Dict[str, Any] = {
    "wallpaper_folder": r"D:\Wallpapers",
    "hotkey": "alt+shift",
    "card_width": 140,
    "card_height": 230,
    "card_radius": 12,
    "close_on_select": True,
    "smooth_scroll": True,
    "auto_start": False,
}


def get_project_root() -> Path:
    """Resolve project root directory."""
    return Path(__file__).resolve().parents[2]


CONFIG_FILE = get_project_root() / "config.json"


def sanitize_config(data: dict) -> dict:
    """Validate and sanitize configuration parameters to safe boundaries."""
    cfg = DEFAULT_CONFIG.copy()
    if not isinstance(data, dict):
        return cfg

    def safe_int(key: str, default: int, min_val: int, max_val: int) -> int:
        try:
            val = int(data.get(key, default))
            return max(min_val, min(val, max_val))
        except (ValueError, TypeError):
            logger.warning(f"Invalid '{key}' value '{data.get(key)}', falling back to {default}")
            return default

    def safe_bool(key: str, default: bool) -> bool:
        val = data.get(key, default)
        return bool(val) if isinstance(val, bool) else default

    cfg["card_width"] = safe_int("card_width", 140, 80, 400)
    cfg["card_height"] = safe_int("card_height", 230, 100, 600)
    cfg["card_radius"] = safe_int("card_radius", 12, 0, 32)
    cfg["close_on_select"] = safe_bool("close_on_select", True)
    cfg["smooth_scroll"] = safe_bool("smooth_scroll", True)
    cfg["auto_start"] = safe_bool("auto_start", False)

    hotkey_raw = data.get("hotkey", "alt+shift")
    cfg["hotkey"] = str(hotkey_raw).strip().lower() if hotkey_raw else "alt+shift"

    folder_raw = data.get("wallpaper_folder", r"D:\Wallpapers")
    cfg["wallpaper_folder"] = str(folder_raw).strip() if folder_raw else r"D:\Wallpapers"

    return cfg


def load_config() -> dict:
    """Load configuration from config.json or create default if missing."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                config = sanitize_config(user_data)
        except Exception as e:
            logger.error(f"Error loading config.json, using defaults: {e}")
            config = DEFAULT_CONFIG.copy()
    else:
        save_config(config)

    # Ensure wallpaper folder exists or create safely
    try:
        folder = Path(config["wallpaper_folder"]).resolve()
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not access or create wallpaper folder {config.get('wallpaper_folder')}: {e}")

    return config


def save_config(config: dict) -> None:
    """Save configuration to config.json."""
    try:
        clean = sanitize_config(config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config.json: {e}")
