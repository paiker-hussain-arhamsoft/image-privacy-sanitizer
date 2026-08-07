"""Basic unit tests for the sanitizer."""

import io

from PIL import Image

from app.integrations import exiftool_clean, mat2_clean
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


def test_external_cleaners_remove_exif():
    img = Image.new("RGB", (64, 64), color=(120, 50, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=b"EXIFTEST", quality=90)
    original = buf.getvalue()

    mat2_result = mat2_clean(original, "jpg")
    if mat2_result is not None:
        with Image.open(io.BytesIO(mat2_result)) as out:
            assert out.info.get("exif") is None

    exiftool_result = exiftool_clean(original, "jpg")
    if exiftool_result is not None:
        with Image.open(io.BytesIO(exiftool_result)) as out:
            assert out.info.get("exif") is None
