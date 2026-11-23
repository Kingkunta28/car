"""Data retention for identity documents (passport / driving licence).

Documents are deleted DOCUMENT_RETENTION_DAYS after the rental ends, or after
the booking was rejected / cancelled / expired. The metadata row is kept
(status PURGED) so the audit trail remains, but the file itself is erased.
"""
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.utils import audit

from .models import BookingDossier, BookingDocument, BookingStatus, DocumentStatus

logger = logging.getLogger(__name__)


def _secure_erase(field_file):
    storage = field_file.storage
    name = field_file.name
    try:
        path = storage.path(name)  # local filesystem only
    except NotImplementedError:
        path = None
    if path and os.path.exists(path):
        size = os.path.getsize(path)
        with open(path, "r+b") as fh:  # overwrite before unlinking
            fh.write(os.urandom(size))
            fh.flush()
            os.fsync(fh.fileno())
    storage.delete(name)


def purge_document(doc: BookingDocument, *, actor=None, reason="retention policy"):
    # Cached PDFs contain copies of uploaded identity documents too. Remove
    # them as well as the original, so retention applies to every stored copy.
    dossier = BookingDossier.objects.filter(booking=doc.booking).first()
    if dossier and dossier.pdf_file:
        _secure_erase(dossier.pdf_file)
        dossier.pdf_file = ""
        dossier.source_digest = ""
        dossier.save(update_fields=["pdf_file", "source_digest", "updated_at"])
    booking = doc.booking
    if booking.voucher_file:
        _secure_erase(booking.voucher_file)
        booking.voucher_file = ""
        booking.voucher_sha256 = ""
        booking.save(update_fields=["voucher_file", "voucher_sha256", "updated_at"])
    if doc.secure_file:
        _secure_erase(doc.secure_file)
    doc.secure_file = ""
    doc.verification_status = DocumentStatus.PURGED
    doc.purged_at = timezone.now()
    doc.save(update_fields=["secure_file", "verification_status", "purged_at"])
    audit("document.purged", actor=actor, target=doc, summary=f"{doc.document_type} purged: {reason}")


def purge_expired_documents(now=None) -> int:
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.DOCUMENT_RETENTION_DAYS)
    closed = [BookingStatus.REJECTED, BookingStatus.CANCELLED, BookingStatus.EXPIRED]
    qs = BookingDocument.objects.exclude(verification_status=DocumentStatus.PURGED).filter(
        Q(booking__return_at__lt=cutoff) | Q(booking__booking_status__in=closed, booking__updated_at__lt=cutoff)
    ).select_related("booking")
    count = 0
    for doc in qs[:500]:
        try:
            purge_document(doc)
            count += 1
        except Exception:
            logger.exception("Failed to purge document %s", doc.pk)
    return count
