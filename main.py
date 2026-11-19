# --- Imports ---
import json
import sys
from pathlib import Path
from src.game_state import GameState


# --- Entry Point ---
def main():
    root = Path(__file__).resolve().parent
    if len(sys.argv) == 2 and sys.argv[1] == "--prepare-android":
        from src.android_packaging import write_spec
        print(write_spec(root))
        return
    settings = json.loads((root / "config" / "settings.json").read_text(encoding="utf-8"))
    save_path = None
    try:
        from kivy.utils import platform
        if platform == "android":
            from android.storage import app_storage_path
            save_path = Path(app_storage_path()) / settings["save_file"]
    except ImportError:
        pass
    state = GameState(root, save_path=save_path)
    from src.mobile_ui import SumerianApp
    SumerianApp(state, root).run()


if __name__ == "__main__":
    main()
