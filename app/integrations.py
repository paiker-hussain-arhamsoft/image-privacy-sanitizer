"""Optional integration with external metadata-scrubbing tools.

MAT2 (https://0xacab.org/jvoisin/mat2) and ExifTool
(https://exiftool.org/) provide deeper structural metadata removal than
Pillow alone. They are invoked only if available on the system PATH.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Callable

logger = logging.getLogger(__name__)


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _run_on_temp(
    data: bytes,
    ext: str,
    runner: Callable[[str], None],
) -> bytes:
    """Write *data* to a temp file with suffix *ext*, run *runner*(path), and read it back."""
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name

    try:
        runner(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def mat2_clean(data: bytes, ext: str) -> bytes | None:
    """Run MAT2 --inplace on *data* if mat2 is installed."""
    if not _tool_available("mat2"):
        return None

    def run(path: str) -> None:
        result = subprocess.run(
            ["mat2", "--inplace", "--unknown-members", "omit", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("mat2 failed: %s", result.stderr)
            raise RuntimeError("mat2 failed")

    try:
        return _run_on_temp(data, ext, run)
    except Exception as exc:  # pragma: no cover
        logger.warning("MAT2 integration skipped: %s", exc)
        return None


def exiftool_clean(data: bytes, ext: str) -> bytes | None:
    """Run ExifTool -all= on *data* if exiftool is installed."""
    if not _tool_available("exiftool"):
        return None

    def run(path: str) -> None:
        # -all= removes all writable metadata, including EXIF, XMP, IPTC, and C2PA/JUMBF.
        result = subprocess.run(
            ["exiftool", "-all=", "-overwrite_original", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("exiftool failed: %s", result.stderr)
            raise RuntimeError("exiftool failed")

    try:
        return _run_on_temp(data, ext, run)
    except Exception as exc:  # pragma: no cover
        logger.warning("ExifTool integration skipped: %s", exc)
        return None


def apply_external_cleaners(data: bytes, ext: str, use_mat2: bool, use_exiftool: bool) -> bytes:
    """Apply MAT2 and/or ExifTool in-place when requested and available."""
    if use_mat2 and _tool_available("mat2"):
        cleaned = mat2_clean(data, ext)
        if cleaned is not None:
            data = cleaned

    if use_exiftool and _tool_available("exiftool"):
        cleaned = exiftool_clean(data, ext)
        if cleaned is not None:
            data = cleaned

    return data
