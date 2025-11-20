from pathlib import Path

from path_dialog_examples import choose_directory

main_game_path_str = choose_directory()
main_game_path = Path(main_game_path_str)
print(main_game_path.resolve())
cards_path = main_game_path / "OPTCGSim_Data" / "StreamingAssets" / "Cards"
print("Cards path:", cards_path.resolve())

from replace_images import replace_alt_cards

replace_alt_cards(cards_path)
