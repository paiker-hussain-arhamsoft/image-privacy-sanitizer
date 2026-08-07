"""Basic unit tests for the sanitizer."""

import io

from PIL import Image

from app.sanitizer import SanitizeOptions, sanitize


def _make_rgb_image() -> bytes:
    img = Image.new("RGB", (64, 64), color=(120, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_metadata_is_stripped():
    original = _make_rgb_image()
    cleaned = sanitize(original, SanitizeOptions(output_format="png"))
    with Image.open(io.BytesIO(cleaned)) as img:
        assert img.format == "PNG"
        assert img.mode == "RGB"
        assert not img.info


def test_jpeg_output_has_no_exif():
    original = _make_rgb_image()
    cleaned = sanitize(original, SanitizeOptions(output_format="jpeg", quality=85))
    with Image.open(io.BytesIO(cleaned)) as img:
        assert img.format == "JPEG"
        assert img.info.get("exif") is None
        assert img.info.get("icc_profile") is None
