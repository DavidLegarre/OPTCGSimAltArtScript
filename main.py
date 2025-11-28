from pathlib import Path

from path_dialog_examples import choose_directory
from replace_images import replace_alt_cards, _load_last_dir, _save_last_dir

# If a saved last directory exists, use it directly; otherwise prompt the user.
print("Selecciona el directorio base de la instalación de OPTCGSim:")
last = _load_last_dir()
if last is not None:
    main_game_path = Path(last)
    print(f"Using saved last directory: {main_game_path.resolve()}")
else:
    main_game_path_str = choose_directory()
    if not main_game_path_str:
        print("No directory selected and no saved last directory found. Exiting.")
        raise SystemExit(1)
    main_game_path = Path(main_game_path_str)
    print(f"Selected directory: {main_game_path.resolve()}")

# Persist the chosen game root so next run can reuse it directly
try:
    _save_last_dir(main_game_path)
except Exception:
    print("Warning: failed to save last directory.")

if main_game_path.name != "Cards":
    main_game_path = main_game_path / "OPTCGSim_Data" / "StreamingAssets" / "Cards"
print("Cards path:", main_game_path.resolve())

replace_alt_cards(main_game_path)
