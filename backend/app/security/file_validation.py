from dataclasses import dataclass
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.config import get_settings
from app.models.attachment import AttachmentKind

settings = get_settings()


def _looks_like_text(content: bytes) -> bool:
    sample = content[:8192]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _is_webp(content: bytes) -> bool:
    return content[:4] == b"RIFF" and content[8:12] == b"WEBP"


# Extension picks which check to run, but the file is only accepted if its actual bytes
# match — a renamed "malware.exe" saved as "invoice.pdf" fails the %PDF- signature check.
# This is why filenames are never trusted for anything beyond this lookup.
SIGNATURE_CHECKS: dict[str, tuple] = {
    ".png": (lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"), "image/png", AttachmentKind.image),
    ".jpg": (lambda b: b.startswith(b"\xff\xd8\xff"), "image/jpeg", AttachmentKind.image),
    ".jpeg": (lambda b: b.startswith(b"\xff\xd8\xff"), "image/jpeg", AttachmentKind.image),
    ".webp": (_is_webp, "image/webp", AttachmentKind.image),
    ".pdf": (lambda b: b.startswith(b"%PDF-"), "application/pdf", AttachmentKind.document),
    ".docx": (
        lambda b: b.startswith(b"PK\x03\x04"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        AttachmentKind.document,
    ),
    ".txt": (_looks_like_text, "text/plain", AttachmentKind.document),
    ".md": (_looks_like_text, "text/markdown", AttachmentKind.document),
    ".csv": (_looks_like_text, "text/csv", AttachmentKind.document),
}


@dataclass
class ValidatedFile:
    kind: AttachmentKind
    mime_type: str
    extension: str


def _get_extension(filename: str) -> str:
    return PurePosixPath(filename.lower()).suffix


def validate_upload(filename: str, content: bytes) -> ValidatedFile:
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")

    extension = _get_extension(filename)
    checker = SIGNATURE_CHECKS.get(extension)
    if not checker:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {extension or 'unknown'}")

    is_valid, mime_type, kind = checker
    if not is_valid(content):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File content does not match its extension")

    limit_mb = settings.max_image_size_mb if kind == AttachmentKind.image else settings.max_document_size_mb
    if len(content) > limit_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds the {limit_mb}MB limit")

    return ValidatedFile(kind=kind, mime_type=mime_type, extension=extension)
