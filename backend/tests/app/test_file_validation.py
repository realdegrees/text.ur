"""Unit tests for the file type validation utility.

Exercises :func:`validate_file_type`, the MIME-to-extension
mapping, and rejection of disallowed / spoofed content.
"""

from __future__ import annotations

import io

import pytest
from core.app_exception import AppException
from util.file_validation import (
    ALLOWED_DOCUMENT_TYPES,
    ALLOWED_IMAGE_TYPES,
    MIME_TO_EXTENSION,
    extension_for_mime,
    validate_file_type,
)

# ── Minimal file headers for content detection ─────────────
# These are the smallest byte sequences that libmagic reliably
# identifies.  Real files are larger but detection only needs
# the first ~8 KiB.

PDF_HEADER = b"%PDF-1.4 minimal"
PNG_HEADER = (
    b"\x89PNG\r\n\x1a\n"  # PNG signature
    b"\x00\x00\x00\rIHDR"  # IHDR chunk
    b"\x00\x00\x00\x01"  # width = 1
    b"\x00\x00\x00\x01"  # height = 1
    b"\x08\x02"  # 8-bit RGB
    b"\x00\x00\x00"  # compression, filter, interlace
    b"\x90wS\xde"  # CRC
)
JPEG_HEADER = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
# WebP is RIFF container; libmagic checks the RIFF + WEBP
WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBPVP8 "


# ── Valid types ────────────────────────────────────────────


def test_validate_pdf() -> None:
    """A valid PDF header is accepted for ALLOWED_DOCUMENT_TYPES."""
    data = io.BytesIO(PDF_HEADER)
    detected = validate_file_type(data, ALLOWED_DOCUMENT_TYPES)
    assert detected == "application/pdf"


def test_validate_png() -> None:
    """A valid PNG header is accepted for ALLOWED_IMAGE_TYPES."""
    data = io.BytesIO(PNG_HEADER)
    detected = validate_file_type(data, ALLOWED_IMAGE_TYPES)
    assert detected == "image/png"


def test_validate_jpeg() -> None:
    """A valid JPEG header is accepted for ALLOWED_IMAGE_TYPES."""
    data = io.BytesIO(JPEG_HEADER)
    detected = validate_file_type(data, ALLOWED_IMAGE_TYPES)
    assert detected == "image/jpeg"


def test_validate_webp() -> None:
    """A valid WebP header is accepted for ALLOWED_IMAGE_TYPES."""
    data = io.BytesIO(WEBP_HEADER)
    detected = validate_file_type(data, ALLOWED_IMAGE_TYPES)
    assert detected == "image/webp"


# ── Rejection ──────────────────────────────────────────────


def test_reject_html_as_document() -> None:
    """An HTML file is rejected when only PDFs are allowed."""
    html = io.BytesIO(b"<html><body>hi</body></html>")
    with pytest.raises(AppException) as exc_info:
        validate_file_type(html, ALLOWED_DOCUMENT_TYPES)
    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail


def test_reject_plain_text_as_image() -> None:
    """Plain text bytes are rejected when only images are allowed."""
    txt = io.BytesIO(b"just some text content here nothing special")
    with pytest.raises(AppException) as exc_info:
        validate_file_type(txt, ALLOWED_IMAGE_TYPES)
    assert exc_info.value.status_code == 400


def test_reject_png_as_document() -> None:
    """A PNG is rejected when only PDF documents are allowed."""
    data = io.BytesIO(PNG_HEADER)
    with pytest.raises(AppException) as exc_info:
        validate_file_type(data, ALLOWED_DOCUMENT_TYPES)
    assert exc_info.value.status_code == 400
    assert "image/png" in exc_info.value.detail


def test_reject_empty_file() -> None:
    """An empty file is rejected (libmagic detects as 'application/x-empty' or similar)."""
    data = io.BytesIO(b"")
    with pytest.raises(AppException):
        validate_file_type(data, ALLOWED_DOCUMENT_TYPES)


# ── Stream position is restored ────────────────────────────


def test_seek_position_restored() -> None:
    """validate_file_type() seeks back to the original position after detection."""
    data = io.BytesIO(PDF_HEADER + b"\x00" * 100)
    # Position starts at 0; validate reads the header and should
    # seek back to 0 after detection.
    assert data.tell() == 0

    validate_file_type(data, ALLOWED_DOCUMENT_TYPES)

    # Position should still be 0 (restored after detection read)
    assert data.tell() == 0


# ── extension_for_mime ─────────────────────────────────────


@pytest.mark.parametrize(
    "mime, expected",
    [
        ("application/pdf", ".pdf"),
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/webp", ".webp"),
        ("application/octet-stream", ""),
        ("text/html", ""),
    ],
)
def test_extension_for_mime(mime: str, expected: str) -> None:
    """extension_for_mime returns the correct extension or empty string."""
    assert extension_for_mime(mime) == expected


# ── MIME_TO_EXTENSION completeness ─────────────────────────


def test_mime_map_covers_all_allowed_types() -> None:
    """Every MIME in ALLOWED_DOCUMENT_TYPES and ALLOWED_IMAGE_TYPES has a mapping."""
    all_allowed = ALLOWED_DOCUMENT_TYPES | ALLOWED_IMAGE_TYPES
    for mime in all_allowed:
        assert mime in MIME_TO_EXTENSION, f"Missing mapping for {mime}"
