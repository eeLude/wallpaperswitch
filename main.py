import sys
from pathlib import Path

# Add src directory to python search path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from wallpaperswitch.app import run_app

if __name__ == "__main__":
    run_app()
