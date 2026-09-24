"""
app/preprocessing/image.py
──────────────────────────
Centralized image preprocessing and validation utilities.
Ensures query images and catalogue images undergo consistent preprocessing
before being passed to the vision encoder.
"""

from pathlib import Path
from typing import Union
from PIL import Image, UnidentifiedImageError


def load_and_preprocess_image(
    image_input: Union[str, Path, Image.Image],
    target_size: tuple[int, int] = (224, 224),
) -> Image.Image:
    """
    Validate, load, and convert an image input into a clean RGB PIL Image.

    Args:
        image_input: Filepath string, Path object, or PIL Image.
        target_size: Optional target size (width, height) for resizing.

    Returns:
        RGB PIL Image ready for encoder processing.

    Raises:
        FileNotFoundError: If the image filepath does not exist.
        ValueError: If the file is not a valid or readable image.
        TypeError: If the input type is unsupported.
    """
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.exists():
            raise FileNotFoundError(f"Image file not found: {p}")
        try:
            img = Image.open(p)
            img.load()  # Force load to catch truncated/corrupt image files
        except (UnidentifiedImageError, OSError) as e:
            raise ValueError(f"Failed to open or parse image file '{p}': {e}") from e
    elif isinstance(image_input, Image.Image):
        img = image_input
    else:
        raise TypeError(
            f"Unsupported image input type '{type(image_input).__name__}'. Expected str, Path, or PIL.Image."
        )

    # Convert color mode to standard RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    return img
