from pathlib import Path
import shutil
import logging
import re

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

# Optional Pillow support for recompressing images before copying
try:
    from PIL import Image

    PIL_AVAILABLE = True
except Exception:
    Image = None
    PIL_AVAILABLE = False

logger.info(f"Pillow available: {PIL_AVAILABLE}")


def _recompress_image(
    path: Path, jpg_quality: int = 80, png_compress_level: int = 9
) -> None:
    """Recompress an image in-place to reduce file size.

    - JPEG: re-save with `quality=jpg_quality` and `optimize=True`.
    - PNG: re-save with `optimize=True` and `compress_level=png_compress_level`.

    If Pillow is not available, this is a no-op.
    """
    if not PIL_AVAILABLE:
        return

    p = Path(path)
    try:
        with Image.open(p) as im:
            fmt = (im.format or "").upper()
            # Prefer suffix check as some images might have format None
            suffix = p.suffix.lower()
            if fmt == "JPEG" or suffix in (".jpg", ".jpeg"):
                # JPEG must be saved in RGB
                if im.mode in ("RGBA", "LA") or (
                    im.mode == "P" and "transparency" in im.info
                ):
                    im = im.convert("RGB")
                im.save(p, format="JPEG", quality=jpg_quality, optimize=True)
            elif fmt == "PNG" or suffix == ".png":
                # Save optimized PNG
                im.save(
                    p, format="PNG", optimize=True, compress_level=png_compress_level
                )
            else:
                # Unknown/unsupported format; do nothing
                return
    except Exception:
        # Let caller handle logging
        raise


ALT_CARDS_DIR_NAME = "data_arts"
LAST_DIR_FILE = Path(__file__).parent / ".last_card_dir"


def _save_last_dir(path: Path) -> None:
    try:
        LAST_DIR_FILE.write_text(str(Path(path).resolve()))
    except Exception:
        logger.exception(f"Failed to save last directory to {LAST_DIR_FILE}")


def _load_last_dir() -> Path | None:
    try:
        if LAST_DIR_FILE.exists():
            text = LAST_DIR_FILE.read_text().strip()
            if text:
                p = Path(text)
                if p.exists() and p.is_dir():
                    return p
    except Exception:
        logger.exception(f"Failed to load last directory from {LAST_DIR_FILE}")
    return None


def replace_alt_cards(card_image_path: Path | str | None):
    """
    Replace card images in card_image_path with images from alt_cards_path
    if they exist.

    This handles alternative filenames such as `OP02-068(PRB02).png` and will
    replace targets like `OP02-068.png` and `OP02-068_small.png` (for png/jpg/jpeg).

    :param card_image_path: Path to the directory containing original card images.
    """
    # Allow None to use the previously saved directory
    if card_image_path is None:
        last = _load_last_dir()
        if last is None:
            logger.error(
                "No card_image_path provided and no saved last directory found."
            )
            return
        card_image_path = last
        logger.info(f"Using saved last directory: {card_image_path}")
    else:
        card_image_path = Path(card_image_path)

        # Note: we do NOT persist the provided `card_image_path` here because
        # callers (e.g. `main.py`) should save the game root (not the Cards subpath).

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
        # Examples:
        # - "OP02-068(PRB02)" -> bases: ["OP02-068(PRB02)", "OP02-068"]
        # - "OP09-051Manga alt" -> bases: ["OP09-051Manga alt", "OP09-051"]
        stem = alt_image.stem
        bases = []
        # keep full stem first
        bases.append(stem)
        # extract card code like OP09-051, ST12-345, EB01-002 anywhere in the stem
        m = re.search(r"(?i)\b(?:OP|ST|EB)\d{2}-\d{3}\b", stem)
        if m:
            code = m.group(0).upper()
            if code not in bases:
                bases.append(code)
        # also handle names with parentheses: take content before '('
        if "(" in stem:
            base = stem.split("(", 1)[0].rstrip()
            if base not in bases:
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

        # Recompress the source image (in-place) to reduce file size if Pillow is available
        if PIL_AVAILABLE:
            try:
                _recompress_image(source_for_copies)
                logger.info(f"Recompressed {source_for_copies} before duplicating")
            except Exception:
                logger.exception(f"Failed to recompress {source_for_copies}")

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
