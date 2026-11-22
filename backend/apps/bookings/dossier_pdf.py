"""Staff-only booking dossier, including faithful rasterized identity documents."""
from decimal import Decimal
from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image as PillowImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from apps.core.models import SiteSettings
from apps.core.pdf import (
    BORDER, CONTENT_W, LIGHT, NAVY, ORANGE, brand_header, build_pdf, chips_row, esc, fitted_image, info_grid,
    line_items, logo_path, p, section, site_dict,
)
from apps.bookings.models import DocumentStatus, DocumentType
from apps.bookings.vehicle_data import booking_vehicle_snapshot


DOCUMENT_LABELS = {
    DocumentType.PASSPORT: ("PASSPORT", "CUSTOMER IDENTIFICATION DOCUMENT"),
    DocumentType.DRIVING_LICENCE: ("DRIVING LICENCE", "DRIVING AUTHORIZATION DOCUMENT"),
}


def _usd(value):
    return f"${Decimal(str(value or 0)):,.2f}"


def _doc_heading(doc_type, doc=None, page=None):
    label, subtitle = DOCUMENT_LABELS[doc_type]
    ref = str(doc.pk).split("-")[0].upper() if doc else "—"
    state = doc.get_verification_status_display().upper() if doc else "NOT PROVIDED"
    if doc and doc.verification_status == DocumentStatus.PURGED:
        state = "PURGED · ORIGINAL FILE REMOVED"
    suffix = f" · PAGE {page}" if page else ""
    return [p(f'<font color="#{ORANGE.hexval()[2:]}"><b>{label}</b></font>', "title_l"),
            p(f"{subtitle}  ·  REF {esc(ref)}{suffix}", "label"),
            p(f"UPLOAD STATUS: {esc(state)}", "small"), Spacer(1, 5 * mm)]


def _document_page(doc_type, doc=None, page_number=None, image=None, unavailable=False):
    site = site_dict(SiteSettings.load())
    reference = doc.booking.booking_reference if doc else "Internal dossier"
    story = [brand_header(site, "Customer document archive", [("Booking ref.", reference)],
                          logo_path(SiteSettings.load()))]
    story.extend(_doc_heading(doc_type, doc, page_number))
    if unavailable:
        story.append(p("This document is unavailable for preview. Use the secure staff document view to inspect the original file.", "body"))
    elif image is not None:
        # A restrained frame keeps the original proportions and leaves the page readable.
        frame = Table([[image]], colWidths=[CONTENT_W - 10 * mm])
        frame.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ]))
        story.append(frame)
    else:
        story.append(p("NOT PROVIDED", "value_b"))
    return story


def _image_flowable(raw, kind):
    source = BytesIO(raw)
    with PillowImage.open(source) as opened:
        original = ImageOps.exif_transpose(opened)
        if getattr(original, "is_animated", False):
            original.seek(0)
        image = original.copy()
    return fitted_image(ImageReader(image), CONTENT_W - 22 * mm, 175 * mm)


def _render_pdf_pages(raw):
    source = pdfium.PdfDocument(raw)
    try:
        for index in range(len(source)):
            page = source[index]
            try:
                width, height = page.get_size()
                # 144 dpi by default, with a pixel cap for unusually large pages.
                scale = min(2.0, (8_000_000 / max(width * height, 1)) ** 0.5)
                bitmap = page.render(scale=scale, rotation=0, fill_color=(255, 255, 255, 255))
                try:
                    pil = bitmap.to_pil()
                    yield index + 1, ImageOps.exif_transpose(pil).copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        source.close()


def _read_doc(doc):
    if not doc.secure_file:
        return None
    doc.secure_file.open("rb")
    try:
        return doc.secure_file.read()
    finally:
        doc.secure_file.close()


def render_booking_dossier(booking) -> bytes:
    """Build a complete internal booking dossier. Never used for customer delivery."""
    settings = SiteSettings.load()
    site = site_dict(settings)
    logo = logo_path(settings)
    meta = [("Booking ref.", booking.booking_reference), ("Created", booking.created_at.strftime("%d %B %Y")),
            ("Currency", booking.currency)]
    story = [brand_header(site, "Internal booking dossier", meta, logo),
             p("CONFIDENTIAL · RESTRICTED STAFF DOCUMENT", "label"), Spacer(1, 3 * mm),
             chips_row([("Booking status", booking.get_booking_status_display(), _booking_tone(booking.booking_status)),
                        ("Payment status", booking.get_payment_status_display(), _payment_tone(booking.payment_status))]),
             section("01 · Customer"), info_grid([
                 ("Full name", booking.customer.full_name), ("Email", booking.customer.email),
                 ("Phone", booking.customer.phone), ("Nationality", booking.customer.nationality or "—"),
             ])]

    vehicle = booking_vehicle_snapshot(booking)
    story += [section("02 · Vehicle & rental"), info_grid([
        ("Vehicle", f"{vehicle.get('name', 'Vehicle')} · {vehicle.get('brand', '')} {vehicle.get('model', '')}{' · ' + str(vehicle['year']) if vehicle.get('year') else ''}"),
        ("Rental duration", f"{booking.rental_days} day(s)"),
        ("Daily rate", _usd(booking.daily_rate)),
        ("Transmission", vehicle.get("transmission_display") or vehicle.get("transmission") or "—"),
        ("Pickup", f"{booking.pickup_date:%d %b %Y} · {booking.pickup_time:%H:%M}"),
        ("Return", f"{booking.return_date:%d %b %Y} · {booking.return_time:%H:%M}"),
    ])]
    story.append(PageBreak())
    story += [brand_header(site, "Journey details", meta, logo),
              p("02  /  THE RENTAL EXPERIENCE", "chapter"),
              p("PICKUP TO RETURN", "editorial")]
    for leg, label in (("pickup", "PICKUP"), ("return", "RETURN")):
        story += [p(label, "label"), info_grid([
            ("Location", booking.location_label(leg)), ("Address", booking.location_address(leg) or "—"),
            ("Instructions", getattr(booking, f"{leg}_instructions") or "—"),
        ])]
    flight = getattr(booking, "flight", None)
    if flight and any((flight.airline_name, flight.flight_number, flight.arrival_date, flight.arrival_time,
                       flight.arrival_airport, flight.notes)):
        story += [section("03 · Arrival details"), info_grid([
            ("Airline", flight.airline_name or "—"), ("Flight", flight.flight_number or "—"),
            ("Arrival", f"{flight.arrival_date or ''} {flight.arrival_time or ''}".strip() or "—"),
            ("Airport", flight.arrival_airport or "—"), ("Notes", flight.notes or "—"),
        ])]
    if booking.customer_notes:
        story += [p("CUSTOMER REQUEST", "label"), p(esc(booking.customer_notes).replace("\n", "<br/>"), "small")]

    story.append(PageBreak())
    story += [brand_header(site, "Financial record", meta, logo),
              p("03  /  SAVED BOOKING PRICES", "chapter")]
    lines = booking.pricing_breakdown.get("lines", [])
    rows = [[line.get("description", ""), str(line.get("quantity", 1)),
             _usd(line.get("unit_price")), _usd(line.get("total"))] for line in lines]
    totals = [("Subtotal", _usd(booking.pricing_breakdown.get("subtotal", booking.grand_total)), False)]
    if booking.tax_amount:
        totals.append(("Tax", _usd(booking.tax_amount), False))
    totals.append(("Grand total", _usd(booking.grand_total), True))
    story += [section("04 · Financial record"),
              line_items(["Description", "Qty", "Unit price", "Amount"], rows,
                         [100 * mm, 18 * mm, 31 * mm, 31 * mm], totals),
              Spacer(1, 4 * mm), info_grid([
                  ("Payment method", booking.get_payment_method_display()),
                  ("Payment status", booking.get_payment_status_display()),
                  ("Amount paid", _usd(booking.amount_paid)), ("Balance due", _usd(booking.balance_due)),
              ])]

    story.append(PageBreak())
    documents = list(booking.documents.order_by("document_type", "uploaded_at"))
    for doc_type in (DocumentType.PASSPORT, DocumentType.DRIVING_LICENCE):
        matches = [doc for doc in documents if doc.document_type == doc_type]
        if not matches:
            story.extend(_document_page(doc_type))
            story.append(PageBreak())
            continue
        for doc in matches:
            raw = _read_doc(doc)
            if doc.verification_status == DocumentStatus.PURGED:
                story.extend(_document_page(doc_type, doc=doc))
                story.append(PageBreak())
                continue
            if not raw:
                story.extend(_document_page(doc_type, doc=doc, unavailable=True))
                story.append(PageBreak())
                continue
            try:
                if doc.file_kind == "pdf":
                    for page_number, image in _render_pdf_pages(raw):
                        story.extend(_document_page(
                            doc_type, doc=doc, page_number=page_number,
                            image=fitted_image(ImageReader(image), CONTENT_W - 22 * mm, 175 * mm),
                        ))
                        story.append(PageBreak())
                else:
                    story.extend(_document_page(doc_type, doc=doc, image=_image_flowable(raw, doc.file_kind)))
                    story.append(PageBreak())
            except Exception:
                # Keep the dossier available without pretending the original rendered correctly.
                story.extend(_document_page(doc_type, doc=doc, unavailable=True))
                story.append(PageBreak())

    story += [brand_header(site, "Important rental information", meta, logo),
              section("05 · Terms & final details")]
    if settings.invoice_terms:
        story.append(p(esc(settings.invoice_terms).replace("\n", "<br/>"), "body"))
    if booking.pickup_instructions or booking.return_instructions:
        story += [Spacer(1, 4 * mm), p("CUSTOMER INSTRUCTIONS", "label")]
        if booking.pickup_instructions:
            story.append(p(f"Pickup · {esc(booking.pickup_instructions)}", "small"))
        if booking.return_instructions:
            story.append(p(f"Return · {esc(booking.return_instructions)}", "small"))
    contact = " · ".join(x for x in (site.get("business_phone"), site.get("business_email"), site.get("website")) if x)
    if contact:
        story += [Spacer(1, 6 * mm), p(esc(contact), "small")]
    story += [Spacer(1, 12 * mm), p("RAFIKI CAR HIRE", "brand"), p("DRIVE ZANZIBAR WITH CONFIDENCE", "tagline")]
    return build_pdf(story, title=f"Internal dossier {booking.booking_reference}", author=site["business_name"],
                     footer=contact, footer_note="CONFIDENTIAL · STAFF ACCESS ONLY")


def _booking_tone(status):
    if status in ("CONFIRMED", "COMPLETED"):
        return "green"
    if status in ("CANCELLED", "REJECTED", "EXPIRED"):
        return "red"
    return "amber"


def _payment_tone(status):
    if status == "PAID":
        return "green"
    if status in ("REFUNDED", "UNPAID"):
        return "red"
    return "amber"
