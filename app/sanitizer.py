"""Privacy-focused image sanitizer.

Strips metadata (EXIF, XMP, ICC, vendor profiles, and other file structure
chunks) and applies a subtle pixel-space perturbation to reduce recoverable
fingerprints. This is intended for privacy/anonymization, not to defeat
content-authenticity systems adversarially.
"""

from __future__ import annotations

import io
import logging
import random
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SanitizeOptions:
    output_format: Literal["jpeg", "png", "webp"] = "png"
    quality: int = 92
    noise_strength: float = 2.0
    axis_offset: int = 1
    apply_noise: bool = True
    apply_offset: bool = True


def _strip_metadata(img: Image.Image) -> Image.Image:
    """Return a copy with no EXIF, XMP, ICC profile, or other info chunks."""
    # Convert to a canonical mode to drop color-profile dependencies.
    if img.mode in ("RGBA", "P", "LA", "L"):
        # For palette images, convert to RGB to strip the palette/colormap.
        if img.mode == "P":
            img = img.convert("RGBA" if "transparency" in img.info else "RGB")
        if img.mode in ("RGBA", "LA"):
            # Flatten transparency onto a white background; removes alpha chunk.
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode == "L":
            img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Force-drop any embedded info dictionaries.
    img.info = {}
    return img


def _add_micro_noise(arr: np.ndarray, strength: float) -> np.ndarray:
    """Add sub-perceptual Gaussian noise to the pixel array."""
    if strength <= 0:
        return arr
    noise = np.random.normal(0, strength, arr.shape)
    perturbed = arr.astype(np.float32) + noise
    return np.clip(perturbed, 0, 255).astype(np.uint8)


def _axis_offset(img: Image.Image, offset: int) -> Image.Image:
    """Shift the image by a few pixels and fill/crop to keep the dimensions."""
    if offset <= 0:
        return img

    dx = random.choice((-offset, offset))
    dy = random.choice((-offset, offset))

    shifted = Image.new(img.mode, img.size, (255, 255, 255))
    shifted.paste(img, (dx, dy))

    # Crop away the exposed border and resize back to original dimensions so the
    # geometric offset is only a 1-pixel class, not a content change.
    w, h = img.size
    crop_box = (max(0, dx), max(0, dy), w - max(0, -dx), h - max(0, -dy))
    if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
        cropped = shifted.crop(crop_box)
        return cropped.resize((w, h), Image.Resampling.LANCZOS)
    return shifted


def sanitize(
    data: bytes,
    options: SanitizeOptions | None = None,
) -> bytes:
    """Sanitize a raw image file and return the cleaned bytes."""
    options = options or SanitizeOptions()

    with Image.open(io.BytesIO(data)) as src:
        # Copy the raw pixel canvas to drop file/container structure.
        img = src.copy()

    img = _strip_metadata(img)
    img = img.convert("RGB")

    # Pixel-space perturbation.
    if options.apply_noise:
        arr = np.array(img)
        arr = _add_micro_noise(arr, options.noise_strength)
        img = Image.fromarray(arr)

    if options.apply_offset:
        img = _axis_offset(img, options.axis_offset)

    out = io.BytesIO()
    fmt = options.output_format.upper()
    save_kwargs: dict = {"optimize": True}

    if fmt == "JPEG":
        save_kwargs["quality"] = options.quality
        save_kwargs["exif"] = b""
        save_kwargs["icc_profile"] = None
    elif fmt == "PNG":
        save_kwargs["compress_level"] = 9
    elif fmt == "WEBP":
        save_kwargs["quality"] = options.quality
    else:
        raise ValueError(f"Unsupported output format: {options.output_format}")

    img.save(out, format=fmt, **save_kwargs)
    return out.getvalue()
