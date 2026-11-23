import uuid
from io import BytesIO
from unittest import skipUnless
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
import pypdfium2 as pdfium
from PIL import Image as PillowImage, ImageDraw
from reportlab.pdfgen.canvas import Canvas
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.bookings.availability import release_expired_holds
from apps.bookings.models import Booking, BookingDocument, BookingStatus
from apps.bookings.retention import purge_expired_documents
from apps.core.tests import factories as f
from apps.invoices.models import Invoice
from apps.notifications.models import DeliveryStatus, NotificationLog

URL = "/api/v1/bookings/"


class BookingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.v = f.vehicle()

    def create(self, payload=None, files=None, **kw):
        payload = payload or f.booking_payload(self.v, **kw)
        with self.captureOnCommitCallbacks(execute=True):
            if files:
                return self.client.post(URL, f.multipart(payload, **files), format="multipart")
            return self.client.post(URL, payload, format="json")

    def guest_headers(self, res):
        return {"HTTP_X_BOOKING_REFERENCE": res.data["booking_reference"],
                "HTTP_X_BOOKING_TOKEN": res.data["access_token"]}

    def test_public_booking_options_expose_current_price_configuration(self):
        response = self.client.get("/api/v1/booking-options/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tax_rate"], "0.00")
        self.assertEqual(response.data["locations"][2]["fee"], "25.00")
        baby_seat = next(extra for extra in response.data["extras"] if extra["code"] == "baby_seat")
        self.assertEqual(baby_seat["price"], "60.00")
        self.assertIsNone(baby_seat["bulk_unit_price"])

    # ---- Happy path ----------------------------------------------------------
    def test_complete_guest_workflow(self):
        res = self.create(pickup_type="OUTSIDE_ZONE", return_type="TOWN", extras={"baby_seat": 2})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["booking_status"], "PENDING_CONFIRMATION")
        self.assertEqual(res.data["payment_status"], "UNPAID")
        # 3 days × 55 + 25 outside zone + 2 × 60 baby seats
        self.assertEqual(res.data["grand_total"], "310.00")
        self.assertTrue(res.data["invoice_number"].startswith(f"RCI-{timezone.localdate().year}-"))

        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.assertTrue(b.blocks_inventory)
        self.assertIsNotNone(b.hold_expires_at)
        self.assertEqual(b.pricing_breakdown["grand_total"], "310.00")
        self.assertEqual(b.extras.get(code="baby_seat").quantity, 2)
        inv = Invoice.objects.get(booking=b)
        self.assertTrue(inv.pdf_file)
        self.assertEqual(inv.total_amount, Decimal("310.00"))

        # Emails to guest and owner, with invoice attached and a secure link (no raw token stored).
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ["amina@example.com", "owner@rafiki.test"])
        guest_mail = next(m for m in mail.outbox if m.to == ["amina@example.com"])
        self.assertEqual(guest_mail.attachments[0][2], "application/pdf")
        self.assertIn("/booking/manage#ref=", guest_mail.alternatives[0][0])
        self.assertEqual(NotificationLog.objects.filter(delivery_status=DeliveryStatus.SENT).count(), 2)
        for log in NotificationLog.objects.all():
            self.assertNotIn(res.data["access_token"], str(log.context))

        # Guest can view their booking and download the invoice PDF.
        track = self.client.get("/api/v1/bookings/track/", **self.guest_headers(res))
        self.assertEqual(track.status_code, 200)
        self.assertEqual(track.data["grand_total"], "310.00")
        pdf = self.client.get("/api/v1/invoices/download/", **self.guest_headers(res))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(pdf.streaming_content).startswith(b"%PDF"))

    def test_frontend_totals_are_ignored(self):
        payload = f.booking_payload(self.v, extras={"baby_seat": 1})
        payload.update(grand_total="1.00", rental_total="0.01", pickup_fee="0")
        res = self.create(payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["grand_total"], "225.00")

    def test_stale_submitted_quote_is_rejected_before_booking_creation(self):
        payload = f.booking_payload(self.v)
        payload["total_amount"] = "1.00"
        res = self.create(payload)
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data["error"]["code"], "validation_error")
        self.assertFalse(Booking.objects.exists())

    def test_matching_submitted_quote_creates_booking(self):
        payload = f.booking_payload(self.v)
        payload["total_amount"] = "165.00"
        res = self.create(payload)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["grand_total"], payload["total_amount"])

    def test_static_catalogue_booking_needs_no_vehicle_row_and_saves_snapshot(self):
        slug = "toyota-rav4-2018"
        snapshot = {
            "id": slug, "slug": slug, "name": "Toyota RAV4", "brand": "Toyota", "model": "RAV4",
            "year": 2018, "category": "SUV", "category_display": "SUV", "description": "Island rental",
            "price_per_day": "35.00", "transmission": "AUTOMATIC", "transmission_display": "Automatic",
            "fuel_type": "PETROL", "fuel_type_display": "Petrol", "passenger_capacity": 5,
            "luggage_capacity": 3, "doors": 5, "features": ["Air conditioning"],
            "availability_status": "AVAILABLE", "availability_display": "Available",
            "main_image": "/images/cars/toyota-rav4-2018.jpeg", "gallery_images": [],
        }
        payload = f.booking_payload(self.v)
        payload.update(vehicle=slug, vehicle_id=slug, vehicle_snapshot=snapshot, daily_rate="35.00")
        self.v.delete()

        res = self.create(payload)
        self.assertEqual(res.status_code, 201, res.data)
        booking = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.assertEqual(res.data["booking_status"], BookingStatus.CONFIRMED)
        self.assertEqual(booking.booking_status, BookingStatus.CONFIRMED)
        self.assertIsNone(booking.vehicle_id)
        self.assertFalse(booking.blocks_inventory)
        self.assertEqual(booking.vehicle_slug, slug)
        self.assertEqual(booking.vehicle_snapshot["name"], "Toyota RAV4")
        self.assertEqual(booking.daily_rate, Decimal("35.00"))
        invoice = Invoice.objects.get(booking=booking)
        self.assertTrue(invoice.pdf_file)
        self.assertTrue(res.data["voucher_available"])
        self.assertTrue(booking.voucher_file.storage.exists(booking.voucher_file.name))
        voucher_response = self.client.get(
            "/api/v1/bookings/confirmation/download/", **self.guest_headers(res),
        )
        self.assertEqual(voucher_response.status_code, 200)
        self.assertIn("private, no-store", voucher_response["Cache-Control"])
        voucher_bytes = b"".join(voucher_response.streaming_content)
        self.assertTrue(voucher_bytes.startswith(b"%PDF"))
        voucher = pdfium.PdfDocument(voucher_bytes)
        voucher_text = "\n".join(voucher[i].get_textpage().get_text_range() for i in range(len(voucher)))
        voucher.close()
        self.assertIn("ACCEPTED", voucher_text)
        self.assertIn(booking.booking_reference, voucher_text)
        self.assertIn("Toyota RAV4", voucher_text)

        # Static catalogue vehicles are always bookable; the catalogue does not
        # participate in Django inventory conflict checks.
        again = self.create(payload)
        self.assertEqual(again.status_code, 201, again.data)
        self.assertEqual(Booking.objects.filter(vehicle_slug=slug).count(), 2)

    def test_voucher_failure_keeps_saved_booking_and_guest_can_retry(self):
        from unittest.mock import patch

        slug = "toyota-rav4-2018"
        snapshot = {
            "id": slug, "slug": slug, "name": "Toyota RAV4", "brand": "Toyota", "model": "RAV4",
            "category": "SUV", "price_per_day": "35.00", "transmission": "AUTOMATIC", "fuel_type": "PETROL",
            "passenger_capacity": 5, "luggage_capacity": 3,
        }
        payload = f.booking_payload(self.v)
        payload.update(vehicle=slug, vehicle_id=slug, vehicle_snapshot=snapshot, daily_rate="35.00")

        with patch("apps.bookings.vouchers.render_confirmation_pdf", side_effect=RuntimeError("renderer unavailable")):
            res = self.create(payload)

        self.assertEqual(res.status_code, 201, res.data)
        self.assertFalse(res.data["voucher_available"])
        booking = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.assertEqual(booking.booking_status, BookingStatus.CONFIRMED)
        self.assertFalse(booking.voucher_file)
        self.assertEqual(Booking.objects.filter(booking_reference=booking.booking_reference).count(), 1)
        pdf = self.client.get("/api/v1/bookings/confirmation/download/", **self.guest_headers(res))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(b"".join(pdf.streaming_content).startswith(b"%PDF"))
        booking.refresh_from_db()
        self.assertTrue(booking.voucher_file.storage.exists(booking.voucher_file.name))

    def test_booking_submission_key_reuses_saved_booking_on_retry(self):
        slug = "toyota-rav4-2018"
        snapshot = {
            "id": slug, "slug": slug, "name": "Toyota RAV4", "brand": "Toyota", "model": "RAV4",
            "category": "SUV", "price_per_day": "35.00", "transmission": "AUTOMATIC", "fuel_type": "PETROL",
            "passenger_capacity": 5, "luggage_capacity": 3,
        }
        payload = f.booking_payload(self.v)
        payload.update(vehicle=slug, vehicle_id=slug, vehicle_snapshot=snapshot, daily_rate="35.00",
                       submission_key=str(uuid.uuid4()))

        first = self.create(payload)
        second = self.create(payload)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(first.data["booking_reference"], second.data["booking_reference"])
        self.assertEqual(Booking.objects.filter(submission_key=payload["submission_key"]).count(), 1)
        self.assertEqual(Booking.objects.filter(vehicle_slug=slug).count(), 1)

    def test_guest_voucher_contains_only_uploaded_identity_document_pages(self):
        slug = "toyota-rav4-2018"
        snapshot = {
            "id": slug, "slug": slug, "name": "Toyota RAV4", "brand": "Toyota", "model": "RAV4",
            "category": "SUV", "price_per_day": "35.00", "transmission": "AUTOMATIC", "fuel_type": "PETROL",
            "passenger_capacity": 5, "luggage_capacity": 3,
        }
        payload = f.booking_payload(self.v, extras={"driving_permit": 1})
        payload.update(vehicle=slug, vehicle_id=slug, vehicle_snapshot=snapshot, daily_rate="35.00")
        self.v.delete()

        image_stream = BytesIO()
        image = PillowImage.new("RGB", (900, 600), "white")
        ImageDraw.Draw(image).text((30, 30), "SYNTHETIC PASSPORT TEST", fill="black")
        image.save(image_stream, format="PNG")
        passport = SimpleUploadedFile("passport.png", image_stream.getvalue(), content_type="image/png")
        pdf_stream = BytesIO()
        canvas = Canvas(pdf_stream)
        canvas.drawString(50, 700, "SYNTHETIC LICENCE TEST PAGE 1")
        canvas.showPage()
        canvas.drawString(50, 700, "SYNTHETIC LICENCE TEST PAGE 2")
        canvas.save()
        licence = SimpleUploadedFile("licence.pdf", pdf_stream.getvalue(), content_type="application/pdf")
        response = self.create(payload, files={"passport": passport, "driving_licence": licence})
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(booking_reference=response.data["booking_reference"])
        self.assertEqual(booking.documents.count(), 2)
        self.assertTrue(booking.voucher_file)

        guest_pdf = self.client.get("/api/v1/bookings/confirmation/download/", **self.guest_headers(response))
        self.assertEqual(guest_pdf.status_code, 200)
        rendered = pdfium.PdfDocument(b"".join(guest_pdf.streaming_content))
        self.assertGreaterEqual(len(rendered), 5)  # two booking pages + image + two uploaded PDF pages
        text = " ".join(rendered[index].get_textpage().get_text_range() for index in range(len(rendered)))
        rendered.close()
        self.assertIn("ACCEPTED", text)
        self.assertIn("PASSPORT PAGE", text)
        self.assertIn("DRIVING LICENCE PAGE", text)

        public_guess = self.client.get(f"/media/{booking.documents.first().secure_file.name}")
        self.assertNotEqual(public_guess.status_code, 200)

    def test_static_catalogue_booking_rejects_unapproved_price(self):
        slug = "toyota-rav4-2018"
        snapshot = {
            "id": slug, "slug": slug, "name": "Toyota RAV4", "brand": "Toyota", "model": "RAV4",
            "category": "SUV", "price_per_day": "1.00", "transmission": "AUTOMATIC", "fuel_type": "PETROL",
            "passenger_capacity": 5, "luggage_capacity": 3,
        }
        payload = f.booking_payload(self.v)
        payload.update(vehicle=slug, vehicle_id=slug, vehicle_snapshot=snapshot, daily_rate="1.00")
        res = self.create(payload)
        self.assertEqual(res.status_code, 400)

    def test_historical_price_unchanged_after_vehicle_price_update(self):
        res = self.create()
        self.v.price_per_day = Decimal("99.00")
        self.v.save()
        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.assertEqual(b.grand_total, Decimal("165.00"))
        self.assertEqual(b.daily_rate, Decimal("55.00"))

    # ---- Validation ----------------------------------------------------------
    def test_town_and_outside_zone_require_address(self):
        p = f.booking_payload(self.v, pickup_type="TOWN")
        p["pickup_address"] = ""
        self.assertEqual(self.create(p).status_code, 400)
        p = f.booking_payload(self.v, return_type="OUTSIDE_ZONE")
        p["return_area"] = ""
        self.assertEqual(self.create(p).status_code, 400)

    def test_invalid_dates_rejected(self):
        p = f.booking_payload(self.v)
        p["return_date"] = p["pickup_date"]
        p["return_time"] = "09:00"
        self.assertEqual(self.create(p).status_code, 400)
        past = (timezone.localdate() - timedelta(days=1)).isoformat()
        p = f.booking_payload(self.v)
        p["pickup_date"] = past
        self.assertEqual(self.create(p).status_code, 400)

    def test_terms_must_be_accepted(self):
        self.assertEqual(self.create(f.booking_payload(self.v, accept_terms=False)).status_code, 400)

    def test_unavailable_vehicle_rejected(self):
        self.v.availability_status = "MAINTENANCE"
        self.v.save()
        self.assertEqual(self.create().status_code, 400)

    # ---- Availability ------------------------------------------------------
    def test_overlapping_booking_rejected(self):
        self.assertEqual(self.create().status_code, 201)
        res = self.create(f.booking_payload(self.v, start_days=11, days=1))
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Booking.objects.count(), 1)

    def test_turnaround_buffer_respected_and_adjacent_booking_allowed(self):
        self.assertEqual(self.create(start_days=10, days=3).status_code, 201)
        # Pickup exactly at the previous return time falls inside the 2-hour turnaround.
        self.assertEqual(self.create(start_days=13, days=2).status_code, 409)
        p = f.booking_payload(self.v, start_days=13, days=2)
        p["pickup_time"] = "13:00"
        self.assertEqual(self.create(p).status_code, 201)

    @skipUnless(connection.vendor == "postgresql", "PostgreSQL-only behaviour")
    def test_database_constraint_blocks_overlap_even_without_app_check(self):
        res = self.create()
        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        clone = Booking.objects.get(pk=b.pk)
        clone.pk = None
        clone.id = None
        clone.booking_reference = "RCH-CLONE01"
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(**{fld.name: getattr(clone, fld.name) for fld in Booking._meta.concrete_fields
                                      if fld.name != "id"})

    def test_expired_hold_releases_vehicle(self):
        res = self.create()
        Booking.objects.update(hold_expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(release_expired_holds(), 1)
        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        self.assertEqual(b.booking_status, BookingStatus.EXPIRED)
        self.assertFalse(b.blocks_inventory)
        self.assertEqual(self.create(f.booking_payload(self.v)).status_code, 201)

    def test_rejected_booking_releases_vehicle(self):
        from apps.bookings.services import change_status
        res = self.create()
        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        change_status(b, BookingStatus.REJECTED, notes="Vehicle in service")
        self.assertEqual(self.create(f.booking_payload(self.v)).status_code, 201)

    def test_public_availability_endpoint_hides_customer_data(self):
        self.create()
        res = self.client.get(f"/api/v1/vehicles/{self.v.slug}/availability/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["busy"]), 1)
        self.assertNotIn("amina", str(res.data).lower())

    # ---- Guest access security -------------------------------------------------
    def test_reference_alone_does_not_grant_access(self):
        res = self.create()
        ref = res.data["booking_reference"]
        for headers in ({"HTTP_X_BOOKING_REFERENCE": ref},
                        {"HTTP_X_BOOKING_REFERENCE": ref, "HTTP_X_BOOKING_TOKEN": "wrong-token"}):
            self.assertEqual(self.client.get("/api/v1/bookings/track/", **headers).status_code, 404)
            self.assertEqual(self.client.get("/api/v1/invoices/download/", **headers).status_code, 404)

    def test_expired_token_rejected(self):
        res = self.create()
        Booking.objects.get().access_tokens.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/v1/bookings/track/", **self.guest_headers(res)).status_code, 404)

    def test_token_for_one_booking_cannot_open_another(self):
        a = self.create()
        b = self.create(f.booking_payload(f.vehicle(name="Suzuki Vitara", model="Vitara")))
        headers = {"HTTP_X_BOOKING_REFERENCE": b.data["booking_reference"],
                   "HTTP_X_BOOKING_TOKEN": a.data["access_token"]}
        self.assertEqual(self.client.get("/api/v1/bookings/track/", **headers).status_code, 404)

    # ---- Driving permit & documents -----------------------------------------
    def test_driving_permit_requires_both_documents(self):
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        self.assertEqual(self.create(p, files={"passport": f.pdf_upload()}).status_code, 400)

    def test_driving_permit_with_documents(self):
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        res = self.create(p, files={"passport": f.pdf_upload(), "driving_licence": f.png_upload()})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["grand_total"], "190.00")
        docs = BookingDocument.objects.all()
        self.assertEqual(docs.count(), 2)
        for d in docs:
            self.assertTrue(d.secure_file.name.startswith("documents/"))
            self.assertNotIn("doc", d.secure_file.name.split("/")[-1].split(".")[0])  # random name
        # Guests see metadata only, never a URL.
        track = self.client.get("/api/v1/bookings/track/", **self.guest_headers(res))
        self.assertNotIn("secure_file", str(track.data))
        # Owner email mentions documents but does not attach them.
        owner = next(m for m in mail.outbox if m.to == ["owner@rafiki.test"])
        self.assertTrue(all(a[0].endswith(".pdf") and "Invoice" in a[0] for a in owner.attachments))

    def test_disguised_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile("passport.pdf", b"MZ\x90\x00 not really a pdf", content_type="application/pdf")
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        self.assertEqual(self.create(p, files={"passport": fake, "driving_licence": f.pdf_upload()}).status_code, 400)

    def test_oversized_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        big = SimpleUploadedFile("passport.pdf", f.PDF_BYTES + b"0" * (9 * 1024 * 1024), content_type="application/pdf")
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        self.assertEqual(self.create(p, files={"passport": big, "driving_licence": f.pdf_upload()}).status_code, 400)

    def test_document_access_restricted_to_finance_roles(self):
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        res = self.create(p, files={"passport": f.pdf_upload(), "driving_licence": f.pdf_upload()})
        self.assertEqual(res.status_code, 201, res.data)
        b = Booking.objects.get(booking_reference=res.data["booking_reference"])
        doc = b.documents.first()
        url = f"/api/v1/admin/bookings/{b.pk}/documents/{doc.pk}/download/"
        self.assertIn(self.client.get(url).status_code, (401, 403))
        self.client.force_authenticate(f.staff(Role.STAFF))
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(f.staff(Role.MANAGER))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_retention_purges_documents(self):
        p = f.booking_payload(self.v, extras={"driving_permit": 1})
        response = self.create(p, files={"passport": f.pdf_upload(), "driving_licence": f.pdf_upload()})
        booking = Booking.objects.get(booking_reference=response.data["booking_reference"])
        voucher_storage, voucher_name = booking.voucher_file.storage, booking.voucher_file.name
        self.assertTrue(voucher_storage.exists(voucher_name))
        doc = BookingDocument.objects.first()
        storage, name = doc.secure_file.storage, doc.secure_file.name
        Booking.objects.update(return_at=timezone.now() - timedelta(days=60), pickup_at=timezone.now() - timedelta(days=63),
                               blocked_until=timezone.now() - timedelta(days=60))
        self.assertEqual(purge_expired_documents(), 2)
        doc.refresh_from_db()
        self.assertEqual(doc.verification_status, "PURGED")
        self.assertFalse(storage.exists(name))
        booking.refresh_from_db()
        self.assertFalse(booking.voucher_file)
        self.assertFalse(voucher_storage.exists(voucher_name))
        # A guest retry creates a clean voucher from the booking snapshot,
        # without the expired identity pages.
        clean_voucher_response = self.client.get(
            "/api/v1/bookings/confirmation/download/", **self.guest_headers(response),
        )
        self.assertEqual(clean_voucher_response.status_code, 200)
        clean_voucher = pdfium.PdfDocument(b"".join(clean_voucher_response.streaming_content))
        clean_text = " ".join(clean_voucher[index].get_textpage().get_text_range()
                               for index in range(len(clean_voucher)))
        clean_voucher.close()
        self.assertNotIn("PASSPORT PAGE", clean_text)

    # ---- Quote endpoint ------------------------------------------------------
    def test_quote_matches_booking_price(self):
        p = f.booking_payload(self.v, pickup_type="OUTSIDE_ZONE", return_type="OUTSIDE_ZONE",
                              extras={"baby_seat": 1, "driving_permit": 1})
        quote = self.client.post("/api/v1/bookings/quote/", {k: p[k] for k in (
            "vehicle", "pickup_date", "pickup_time", "return_date", "return_time", "pickup_type", "return_type",
            "extras")}, format="json")
        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.data["grand_total"], "275.00")
        self.assertNotIn("available", quote.data)
