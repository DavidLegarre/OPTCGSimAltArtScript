"""Module for replacing card images with alternative artwork versions."""

from pathlib import Path
import shutil
import logging
import re
from typing import Optional
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False

logger.info(f"Pillow available: {PIL_AVAILABLE}")


# Constants
ALT_CARDS_DIR_NAME = "data_arts"
LAST_DIR_FILE = Path(__file__).parent / ".last_card_dir"
ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg")
CARD_CODE_PATTERN = re.compile(r"(?i)(?:OP|ST|EB)\d{2}-\d{3}")
PNG_COMPRESS_LEVEL = 9


@dataclass
class CardNameBases:
    """Container for different base name variations of a card."""
    full_stem: str
    card_code: Optional[str]
    before_parenthesis: Optional[str]

    @classmethod
    def from_filename(cls, stem: str) -> "CardNameBases":
        """Extract all possible base names from an alt image filename.
        
        Examples:
            - "OP02-068(PRB02)" -> full_stem, "OP02-068", "OP02-068"
            - "OP09-051Manga alt" -> full_stem, "OP09-051", None
        """
        card_code = None
        match = CARD_CODE_PATTERN.search(stem)
        if match:
            card_code = match.group(0).upper()
        
        before_parenthesis = None
        if "(" in stem:
            before_parenthesis = stem.split("(", 1)[0].rstrip()
        
        return cls(full_stem=stem, card_code=card_code, before_parenthesis=before_parenthesis)
    
    def get_unique_bases(self) -> list[str]:
        """Return unique base names in priority order."""
        bases = [self.full_stem]
        
        if self.card_code and self.card_code not in bases:
            bases.append(self.card_code)
        
        if self.before_parenthesis and self.before_parenthesis not in bases:
            bases.append(self.before_parenthesis)
        
        return bases


class ImageConverter:
    """Handles image format conversion and optimization."""
    
    @staticmethod
    def convert_to_rgb(image: Image.Image) -> Image.Image:
        """Convert image to RGB mode, handling transparency with white background."""
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            return background
        elif image.mode != "RGB":
            return image.convert("RGB")
        return image
    
    @staticmethod
    def save_as_png(source_path: Path, target_path: Path) -> None:
        """Load an image and save it as optimized PNG."""
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow is not available for image conversion")
        
        with Image.open(source_path) as img:
            rgb_image = ImageConverter.convert_to_rgb(img)
            rgb_image.save(target_path, format="PNG", optimize=True, compress_level=PNG_COMPRESS_LEVEL)


class TargetFinder:
    """Finds target card images to replace."""
    
    def __init__(self, card_image_path: Path):
        self.card_image_path = card_image_path
    
    def find_targets(self, base_names: list[str]) -> list[Path]:
        """Find all existing target files that match the given base names."""
        targets = []
        for base in base_names:
            for ext in ALLOWED_EXTENSIONS:
                for suffix in ("", "_small"):
                    candidate_name = f"{base}{suffix}{ext}"
                    matches = list(self.card_image_path.rglob(candidate_name))
                    targets.extend(matches)
        return targets
    
    @staticmethod
    def sort_targets_by_priority(targets: list[Path]) -> list[Path]:
        """Sort targets to prioritize non-small files and shallower paths."""
        return sorted(targets, key=lambda p: (p.name.endswith("_small"), len(p.parts), p.name))


class TargetPathConverter:
    """Converts target paths from various formats to PNG."""
    
    @staticmethod
    def convert_to_png_paths(targets: list[Path]) -> list[Path]:
        """Convert all target paths to use .png extension, removing old non-PNG files."""
        png_targets = []
        
        for target in targets:
            if target.suffix.lower() != '.png':
                png_target = target.with_suffix('.png')
                png_targets.append(png_target)
                TargetPathConverter._remove_old_file(target)
            else:
                png_targets.append(target)
        
        return png_targets
    
    @staticmethod
    def _remove_old_file(file_path: Path) -> None:
        """Remove old non-PNG file if it exists."""
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Removed old non-PNG file: {file_path}")
            except Exception:
                logger.exception(f"Failed to remove old file {file_path}")


class AltImageProcessor:
    """Processes a single alt image replacement operation."""
    
    def __init__(self, alt_image: Path, card_image_path: Path):
        self.alt_image = alt_image
        self.target_finder = TargetFinder(card_image_path)
    
    def process(self) -> None:
        """Execute the full replacement process for this alt image."""
        logger.info(f"Processing alt image: {self.alt_image}")
        
        # Extract base names from filename
        bases = CardNameBases.from_filename(self.alt_image.stem)
        unique_bases = bases.get_unique_bases()
        
        # Find matching target files
        targets = self.target_finder.find_targets(unique_bases)
        if not targets:
            logger.info(f"No matching targets found for alt image: {self.alt_image}")
            return
        
        logger.info(f"Matched targets for {self.alt_image}: {[str(p) for p in targets]}")
        
        # Sort and convert targets to PNG paths
        sorted_targets = self.target_finder.sort_targets_by_priority(targets)
        png_targets = TargetPathConverter.convert_to_png_paths(sorted_targets)
        
        # Convert and save the alt image as PNG
        self._convert_and_save_primary_target(png_targets[0])
        
        # Copy to remaining targets
        self._copy_to_remaining_targets(png_targets)
        
        # Clean up original alt image
        self._remove_alt_image()
    
    def _convert_and_save_primary_target(self, primary_target: Path) -> None:
        """Convert the alt image to PNG and save to the primary target."""
        if not PIL_AVAILABLE:
            logger.warning(f"Pillow not available, cannot convert {self.alt_image} to PNG format")
            raise RuntimeError("Pillow is required for image conversion")
        
        try:
            ImageConverter.save_as_png(self.alt_image, primary_target)
            logger.info(f"Converted and saved {self.alt_image} -> {primary_target} as PNG")
        except Exception:
            logger.exception(f"Failed to convert {self.alt_image} to PNG at {primary_target}")
            raise
    
    def _copy_to_remaining_targets(self, png_targets: list[Path]) -> None:
        """Copy the primary PNG to all other target locations."""
        if len(png_targets) <= 1:
            return
        
        primary_target = png_targets[0]
        for other_target in png_targets[1:]:
            try:
                shutil.copy2(primary_target, other_target)
                logger.info(f"Copied PNG {primary_target} -> {other_target}")
            except Exception:
                logger.exception(f"Failed to copy {primary_target} -> {other_target}")
    
    def _remove_alt_image(self) -> None:
        """Remove the original alt image file."""
        try:
            self.alt_image.unlink()
            logger.info(f"Removed original alt image: {self.alt_image}")
        except Exception:
            logger.exception(f"Failed to remove original alt image {self.alt_image}")


class LastDirectoryManager:
    """Manages persistence of the last used directory."""
    
    @staticmethod
    def save(path: Path) -> None:
        """Save the last used directory path."""
        try:
            LAST_DIR_FILE.write_text(str(path.resolve()))
        except Exception:
            logger.exception(f"Failed to save last directory to {LAST_DIR_FILE}")
    
    @staticmethod
    def load() -> Optional[Path]:
        """Load the last used directory path, if it exists and is valid."""
        try:
            if not LAST_DIR_FILE.exists():
                return None
            
            text = LAST_DIR_FILE.read_text().strip()
            if not text:
                return None
            
            path = Path(text)
            if path.exists() and path.is_dir():
                return path
        except Exception:
            logger.exception(f"Failed to load last directory from {LAST_DIR_FILE}")
        
        return None


def _get_card_image_path(card_image_path: Optional[Path | str]) -> Optional[Path]:
    """Resolve and validate the card image path."""
    if card_image_path is None:
        last_dir = LastDirectoryManager.load()
        if last_dir is None:
            logger.error("No card_image_path provided and no saved last directory found.")
            return None
        logger.info(f"Using saved last directory: {last_dir}")
        return last_dir
    
    return Path(card_image_path)


def _get_alt_images(alt_cards_path: Path) -> list[Path]:
    """Get all valid alt card images from the alt cards directory."""
    return [
        p for p in alt_cards_path.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ]


def _create_progress_iterator(items: list[Path]):
    """Create a progress iterator with tqdm if available."""
    if tqdm is not None:
        return tqdm(items, desc="Replacing alt images", unit="file")
    return items


def replace_alt_cards(card_image_path: Optional[Path | str] = None) -> None:
    """Replace card images with alternative artwork versions.
    
    Searches for alt card images in the data_arts directory and replaces
    matching card images in the game directory. All images are converted
    to PNG format during the replacement process.
    
    Args:
        card_image_path: Path to the directory containing original card images.
                        If None, uses the last saved directory.
    
    Example filenames handled:
        - "OP02-068(PRB02).png" -> replaces "OP02-068.png" and "OP02-068_small.png"
        - "OP09-051alt.jpg" -> replaces "OP09-051.png" and "OP09-051_small.png"
    """
    resolved_path = _get_card_image_path(card_image_path)
    if resolved_path is None:
        return
    
    logger.info(f"Starting replacement of alt card images in {resolved_path.resolve()}...")
    
    alt_cards_path = Path(__file__).parent / ALT_CARDS_DIR_NAME
    alt_images = _get_alt_images(alt_cards_path)
    
    for alt_image in _create_progress_iterator(alt_images):
        try:
            processor = AltImageProcessor(alt_image, resolved_path)
            processor.process()
        except Exception:
            # Exception already logged by processor, continue with next image
            continue


# Expose public API
_save_last_dir = LastDirectoryManager.save
_load_last_dir = LastDirectoryManager.load
