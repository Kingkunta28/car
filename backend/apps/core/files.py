"""Upload validation and private-file helpers.

Files are validated by size, extension AND magic bytes (the declared
content-type from the browser is never trusted). Stored names are random
UUIDs so original filenames never reach the filesystem.
"""
import hashlib
import mimetypes
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import storages
from django.http import FileResponse
from django.utils.deconstruct import deconstructible

SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF"],
}
EXT_ALIASES = {"jpeg": "jpg"}
DOCUMENT_TYPES = ("pdf", "jpg", "png", "webp")
IMAGE_TYPES = ("jpg", "png", "webp")


def private_storage():
    return storages["private"]


def _detect(head: bytes) -> str | None:
    for kind, sigs in SIGNATURES.items():
        for sig in sigs:
            if head.startswith(sig):
                if kind == "webp" and head[8:12] != b"WEBP":
                    continue
                return kind
    return None


def validate_upload(f, allowed=DOCUMENT_TYPES, max_mb: int | None = None) -> str:
    """Validate an uploaded file. Returns the detected kind ('pdf', 'jpg', ...)."""
    max_mb = max_mb or settings.MAX_UPLOAD_SIZE_MB
    if f is None:
        raise ValidationError("No file was uploaded.")
    if f.size == 0:
        raise ValidationError("The uploaded file is empty.")
    if f.size > max_mb * 1024 * 1024:
        raise ValidationError(f"File is too large. The maximum size is {max_mb} MB.")
    ext = Path(f.name or "").suffix.lower().lstrip(".")
    ext = EXT_ALIASES.get(ext, ext)
    if ext not in allowed:
        raise ValidationError(f"Unsupported file type. Allowed: {', '.join(a.upper() for a in allowed)}.")
    pos = f.tell() if hasattr(f, "tell") else 0
    f.seek(0)
    head = f.read(16)
    f.seek(pos)
    kind = _detect(head)
    if kind != ext:
        raise ValidationError("The file content does not match its extension.")
    return kind


def file_sha256(f) -> str:
    h = hashlib.sha256()
    f.seek(0)
    for chunk in f.chunks() if hasattr(f, "chunks") else iter(lambda: f.read(65536), b""):
        h.update(chunk)
    f.seek(0)
    return h.hexdigest()


@deconstructible
class RandomUploadPath:
    """``upload_to`` callable that discards the original filename."""

    def __init__(self, folder: str):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()
        ext = ".jpg" if ext == ".jpeg" else ext
        return f"{self.folder}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, RandomUploadPath) and other.folder == self.folder


def private_file_response(field_file, download_name: str, as_attachment=True) -> FileResponse:
    content_type, _ = mimetypes.guess_type(download_name)
    field_file.open("rb")
    resp = FileResponse(field_file, as_attachment=as_attachment, filename=download_name,
                        content_type=content_type or "application/octet-stream")
    resp["Cache-Control"] = "private, no-store, max-age=0"
    resp["X-Content-Type-Options"] = "nosniff"
    return resp
