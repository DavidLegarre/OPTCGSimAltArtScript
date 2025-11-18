from pathlib import Path
from tkinter import filedialog

main_game_path_str = input("Enter the path to the main game directory: ")

main_game_path = Path(main_game_path_str)
print(main_game_path.resolve())

CARDS_PATH = main_game_path / "OPTCGSim_Data" / "StreamingAssets" / "Cards"

print("Cards path:", CARDS_PATH.resolve())
