"""Generic content-based file type validation using libmagic.

Provides a single entry point :func:`validate_file_type` that
detects the MIME type from the actual file bytes (not the
client-supplied ``Content-Type`` header) and rejects files whose
detected type is not in the caller's allow-list.

Type sets are defined here so that upload endpoints only need to
reference a constant rather than duplicating MIME strings.
"""

from typing import BinaryIO

import magic
from core.app_exception import AppException
from models.enums import AppErrorCode

# ── Allowed type sets ───────────────────────────────────────
ALLOWED_DOCUMENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
    }
)

ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)

# ── MIME ↔ extension mapping ────────────────────────────────
MIME_TO_EXTENSION: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def extension_for_mime(content_type: str) -> str:
    """Return a file extension (including leading dot) for *content_type*.

    Falls back to an empty string for unknown types.
    """
    return MIME_TO_EXTENSION.get(content_type, "")


# ── Validation ──────────────────────────────────────────────
# A single ``magic.Magic`` instance is thread-safe for
# ``from_buffer`` calls after construction.
_mime_detector = magic.Magic(mime=True)

# How many bytes to read for detection.  libmagic typically
# needs far fewer but 8 KiB covers all common formats.
_DETECTION_BYTES = 8192


def validate_file_type(
    data: BinaryIO,
    allowed_types: frozenset[str],
) -> str:
    """Detect the MIME type of *data* and validate it.

    Reads up to :data:`_DETECTION_BYTES` from the current
    position, detects the type via ``libmagic``, then **seeks
    back** to the original position so the caller can continue
    reading from where it left off.

    Returns the detected MIME type string on success.

    Raises :class:`AppException` (400) when the detected type is
    not in *allowed_types*.
    """
    pos = data.tell()
    sample = data.read(_DETECTION_BYTES)
    data.seek(pos)

    detected: str = _mime_detector.from_buffer(sample)

    if detected not in allowed_types:
        friendly = ", ".join(sorted(allowed_types))
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail=(f"Unsupported file type: {detected}. Allowed types: {friendly}."),
        )

    return detected
