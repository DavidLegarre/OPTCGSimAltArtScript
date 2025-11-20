from pathlib import Path
import shutil
import logging

try:
    from loguru import logger
except Exception:
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

try:
    from tqdm.auto import tqdm
except Exception:
    tqdm = None

ALT_CARDS_DIR_NAME = "data_arts"


def replace_alt_cards(card_image_path: Path):
    """
    Replace card images in card_image_path with images from alt_cards_path
    if they exist.

    This handles alternative filenames such as `OP02-068(PRB02).png` and will
    replace targets like `OP02-068.png` and `OP02-068_small.png` (for png/jpg/jpeg).

    :param card_image_path: Path to the directory containing original card images.
    """
    logger.info(
        f"Starting replacement of alt card images in {card_image_path.resolve()}..."
    )
    alt_cards_path = Path(__file__).parent / ALT_CARDS_DIR_NAME
    allowed_exts = (".png", ".jpg", ".jpeg")

    # Gather alt images up-front so we can show a progress bar with tqdm (if available)
    all_alt_images = [
        p
        for p in alt_cards_path.iterdir()
        if p.is_file() and p.suffix.lower() in allowed_exts
    ]
    iterator = (
        tqdm(all_alt_images, desc="Replacing alt images", unit="file")
        if tqdm is not None
        else all_alt_images
    )

    for alt_image in iterator:
        if not alt_image.is_file():
            continue
        if alt_image.suffix.lower() not in allowed_exts:
            continue

        # Log the alt image path being processed
        logger.info(f"Processing alt image: {alt_image}")

        # Compute candidate bases from the alt image stem.
        # Example: "OP02-068(PRB02)" -> bases: ["OP02-068(PRB02)", "OP02-068"]
        stem = alt_image.stem
        bases = [stem]
        if "(" in stem:
            base = stem.split("(", 1)[0].rstrip()
            bases.append(base)

        # Build list of existing candidate targets to replace (search recursively in subdirs)
        targets = []
        for base in bases:
            for ext in allowed_exts:
                for suffix in ("", "_small"):
                    candidate_name = f"{base}{suffix}{ext}"
                    # search recursively for files with this exact name
                    matches = list(card_image_path.rglob(candidate_name))
                    if matches:
                        targets.extend(matches)

        if not targets:
            logger.info(f"No matching targets found for alt image: {alt_image}")
            continue

        # Log matched original target paths
        logger.info(f"Matched targets for {alt_image}: {[str(p) for p in targets]}")

        # Prefer renaming to a normal (non-_small) target first, and prefer shallower paths
        targets.sort(key=lambda p: (p.name.endswith("_small"), len(p.parts), p.name))

        first_target = targets[0]

        renamed = False
        try:
            # Use Path.replace to move and overwrite the existing target atomically when possible
            alt_image.replace(first_target)
            logger.info(f"Replaced (moved) {alt_image} -> {first_target}")
            renamed = True
            source_for_copies = first_target
        except Exception:
            # Fall back to copying when replace/rename isn't possible
            try:
                shutil.copy2(alt_image, first_target)
                logger.info(f"Copied {alt_image} -> {first_target}")
            except Exception:
                logger.exception(f"Failed to copy {alt_image} -> {first_target}")
                continue
            source_for_copies = first_target

        for other in targets[1:]:
            try:
                shutil.copy2(source_for_copies, other)
                logger.info(f"Copied {source_for_copies} -> {other}")
            except Exception:
                logger.exception(f"Failed to copy {source_for_copies} -> {other}")

        # If we copied (rename/replace failed), remove original alt image
        if not renamed:
            try:
                alt_image.unlink()
            except Exception:
                logger.exception(f"Failed to remove original alt image {alt_image}")
