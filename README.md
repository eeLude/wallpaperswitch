# WallpaperSwitch 🖼️

An aesthetic, minimalist desktop wallpaper dock for Windows. Press a global hotkey to pop up a floating translucent strip of wallpaper cards directly on your desktop, scroll smoothly, and apply any wallpaper with a single click.

---

## ✨ Features

- **Double-Click Desktop**: Double-click anywhere on empty desktop wallpaper space to instantly pop up the wallpaper dock. Zero interference when inside games, browsers, or other apps!
- **Safe Global Hotkey**: Press `Alt + Shift + W` (customizable) to toggle the dock from any application.
- **Aesthetic Dock UI**: Translucent obsidian backdrop hugging rounded portrait cards with smooth hover elevation and lighting sheen.
- **Fluid Navigation**:
  - **Mouse Wheel**: Vertical scrolling automatically pans horizontally.
  - **Drag-to-Scroll**: Click and drag across cards for fluid touch/mouse panning.
  - **Keyboard**: `Left` / `Right` arrows to navigate, `Escape` to dismiss.
- **1-Click Apply**: Click any card to immediately set Windows wallpaper in high-resolution "Fill" mode. Active wallpaper is marked with a checkmark badge.
- **Multi-Monitor Aware**: Automatically opens centered on the monitor where your mouse cursor is located.
- **Single-Instance Protection**: Named Win32 Mutex prevents duplicate background processes.
- **Live Folder Watching & Drag-and-Drop**: Monitors your wallpaper directory (`D:\Wallpapers`) and accepts dragged image files directly onto the dock.
- **Non-blocking Caching**: Generates $2\times$ supersampled thumbnails in background threads for 60 FPS scrolling without UI lag.
- **System Tray**: Resides quietly in the Windows system tray with a folder picker, double-click toggle, and "Run at Windows Startup" toggle.

---

## 🚀 Quick Start

### Prerequisites
- Windows 10 or Windows 11
- Python 3.10+

### Installation

```bash
git clone https://github.com/<your-username>/wallpaperSwitch.git
cd wallpaperSwitch
pip install -r requirements.txt
```

### Running

- **Everyday Background Run** (no console window):  
  Double-click `start_silent.vbs`
- **Debug Run** (with console logs):  
  Double-click `start.bat` or run:
  ```bash
  python main.py
  ```

---

## ⌨️ Controls

| Action | Control |
| :--- | :--- |
| **Open on Desktop** | **Double-click empty desktop wallpaper** |
| **Toggle via Keyboard** | `Alt + Shift + W` (or custom hotkey) |
| **Scroll Wallpapers** | Mouse Wheel / Click-and-drag / `Left` & `Right` Arrow keys |
| **Set Wallpaper** | Click any card |
| **Dismiss Dock** | `Escape` / Click outside / Re-press hotkey |
| **Add Wallpapers** | Drag and drop images onto the dock |

---

## ⚙️ Configuration (`config.json`)

On first launch, `config.json` is automatically created at the project root:

```json
{
    "wallpaper_folder": "D:\\Wallpapers",
    "hotkey": "alt+shift+w",
    "enable_hotkey": true,
    "desktop_double_click": true,
    "card_width": 140,
    "card_height": 230,
    "card_radius": 12,
    "close_on_select": true,
    "smooth_scroll": true,
    "auto_start": false
}
```

- `desktop_double_click`: Enables opening the selector by double-clicking on empty desktop space (`true`/`false`).
- `wallpaper_folder`: Directory containing your wallpapers (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`).
- `hotkey`: Activation keyboard shortcut (default `alt+shift+w`, won't conflict with gaming).
- `enable_hotkey`: Toggle keyboard hotkey listener (`true`/`false`).
- `close_on_select`: Automatically dismiss the dock after applying a wallpaper (`true`/`false`).

---

## 📁 Project Structure

```
wallpaperSwitch/
├── .gitignore               # Clean git exclusions
├── LICENSE                  # MIT License
├── README.md                # Documentation
├── requirements.txt         # Pinned runtime dependencies
├── pyproject.toml           # Standard Python package metadata
├── config.example.json      # Configuration template
├── start.bat                # Windows console launcher
├── start_silent.vbs         # Background launcher (silent)
├── main.py                  # Root execution entrypoint
└── src/
    └── wallpaperswitch/     # Core package
        ├── __init__.py
        ├── app.py           # Application coordinator & mutex guard
        ├── config.py        # Config loader & validator
        ├── hotkey_manager.py# Global keyboard listener
        ├── thumbnail_cache.py# Multi-threaded thumbnail caching
        ├── tray_app.py      # System tray icon & menus
        ├── ui_cards.py      # Rounded wallpaper card widget
        ├── ui_overlay.py    # Translucent floating dock window
        └── wallpaper_engine.py # Win32 wallpaper & registry engine
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
