from io import BytesIO

import pypdfium2 as pdfium
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage, ImageDraw
from reportlab.pdfgen.canvas import Canvas
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.bookings.models import Booking, BookingDocument, DocumentType
from apps.bookings.dossier import ensure_dossier
from apps.bookings.retention import purge_document
from apps.core.tests import factories as f
from apps.core.utils import sha256_hex


class BookingDossierTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        vehicle = f.vehicle()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/v1/bookings/", f.booking_payload(vehicle), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.booking = Booking.objects.get(booking_reference=response.data["booking_reference"])

    def _passport_image(self):
        stream = BytesIO()
        image = PillowImage.new("RGB", (900, 600), "white")
        ImageDraw.Draw(image).text((30, 30), "SYNTHETIC TEST DOCUMENT · PASSPORT", fill="black")
        image.save(stream, format="JPEG")
        return stream.getvalue()

    def _licence_pdf(self):
        stream = BytesIO()
        canvas = Canvas(stream)
        canvas.drawString(50, 700, "SYNTHETIC TEST DOCUMENT · LICENCE PAGE 1")
        canvas.showPage()
        canvas.drawString(50, 700, "SYNTHETIC TEST DOCUMENT · LICENCE PAGE 2")
        canvas.save()
        return stream.getvalue()

    def _add_doc(self, doc_type, file_kind, filename, content):
        doc = BookingDocument(booking=self.booking, document_type=doc_type, file_kind=file_kind,
                              file_size=len(content), sha256=sha256_hex(content))
        doc.secure_file.save(filename, ContentFile(content), save=False)
        doc.save()
        return doc

    def test_dossier_contains_original_image_and_every_uploaded_pdf_page_and_is_private(self):
        self._add_doc(DocumentType.PASSPORT, "jpg", "passport.jpg", self._passport_image())
        self._add_doc(DocumentType.DRIVING_LICENCE, "pdf", "licence.pdf", self._licence_pdf())

        self.client.force_authenticate(user=f.staff(Role.STAFF))
        denied = self.client.get(f"/api/v1/admin/bookings/{self.booking.pk}/dossier/")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(user=f.staff(Role.MANAGER))
        response = self.client.get(f"/api/v1/admin/bookings/{self.booking.pk}/dossier/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("private, no-store", response["Cache-Control"])
        content = b"".join(response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))

        dossier = self.booking.dossier
        self.assertTrue(dossier.pdf_file.storage.exists(dossier.pdf_file.name))
        rendered = pdfium.PdfDocument(content)
        self.assertEqual(len(rendered), 7)  # cover, journey, finance, passport, two source PDF pages, terms
        rendered.close()

    def test_dossier_shows_missing_documents_without_inventing_files(self):
        self.client.force_authenticate(user=f.staff(Role.MANAGER))
        response = self.client.get(f"/api/v1/admin/bookings/{self.booking.pk}/dossier/")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))
        rendered = pdfium.PdfDocument(content)
        text = " ".join(rendered[index].get_textpage().get_text_range() for index in range(len(rendered)))
        rendered.close()
        self.assertIn("NOT PROVIDED", text)
        self.assertFalse(self.booking.documents.exists())

    def test_identity_retention_also_removes_cached_dossier_copy(self):
        doc = self._add_doc(DocumentType.PASSPORT, "jpg", "passport.jpg", self._passport_image())
        dossier = ensure_dossier(self.booking)
        stored_name = dossier.pdf_file.name
        storage = dossier.pdf_file.storage
        self.assertTrue(storage.exists(stored_name))

        purge_document(doc, reason="test retention")

        dossier.refresh_from_db()
        self.assertFalse(dossier.pdf_file)
        self.assertFalse(storage.exists(stored_name))

    def test_booking_with_identity_uploads_stores_staff_dossier_without_blocking_booking(self):
        vehicle = f.vehicle()
        payload = f.booking_payload(vehicle, extras={"driving_permit": 1})
        files = {
            "passport": SimpleUploadedFile("passport.jpg", self._passport_image(), content_type="image/jpeg"),
            "driving_licence": SimpleUploadedFile("licence.pdf", self._licence_pdf(), content_type="application/pdf"),
        }
        response = self.client.post("/api/v1/bookings/", f.multipart(payload, **files), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(booking_reference=response.data["booking_reference"])
        self.assertEqual(booking.documents.count(), 2)
        self.assertTrue(booking.dossier.pdf_file)
        self.assertTrue(booking.dossier.pdf_file.storage.exists(booking.dossier.pdf_file.name))
