from decimal import Decimal, InvalidOperation

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, PageBreak, Spacer, Table, TableStyle

from apps.core.pdf import (
    BORDER, CONTENT_W, LIGHT, NAVY, ORANGE, brand_header, build_pdf, chips_row, esc, fitted_image, image_reader,
    info_grid, line_items, p, section,
)


def usd(value) -> str:
    """Format stored monetary values without converting through binary floats."""
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0.00")
    return f"${amount:,.2f}"


class RouteDivider(Flowable):
    """A quiet line and paired markers linking pickup to return."""

    def __init__(self, width=CONTENT_W):
        super().__init__()
        self.width, self.height = width, 12 * mm

    def wrap(self, available_width, available_height):
        self.width = min(self.width, available_width)
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        y, left, right = self.height / 2, 7 * mm, self.width - 7 * mm
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(1)
        canvas.line(left, y, right, y)
        canvas.setFillColor(ORANGE)
        canvas.circle(left, y, 2.3 * mm, stroke=0, fill=1)
        canvas.setFillColor(NAVY)
        canvas.circle(right, y, 2.3 * mm, stroke=0, fill=1)
        canvas.restoreState()


def _status_tone(status):
    key = str(status).lower()
    if any(word in key for word in ("paid", "confirm", "complete")):
        return "green"
    if any(word in key for word in ("cancel", "reject", "refund", "unpaid")):
        return "red"
    if any(word in key for word in ("pending", "verification")):
        return "amber"
    return "slate"


def _pickup_return(trip):
    cells = []
    for label, key, address_key, date_key, instructions_key, color in (
        ("PICKUP", "pickup_location", "pickup_address", "pickup_datetime", "pickup_instructions", ORANGE),
        ("RETURN", "return_location", "return_address", "return_datetime", "return_instructions", NAVY),
    ):
        tint = f"#{color.hexval()[2:]}"
        content = [p(f'<font color="{tint}"><b>{label}</b></font>', "label"),
                   p(esc(trip.get(key) or "—"), "value_b"), p(esc(trip.get(date_key) or "—"), "body")]
        if trip.get(address_key):
            content.append(p(esc(trip[address_key]), "small"))
        if trip.get(instructions_key):
            content += [Spacer(1, 2 * mm), p(f'<b>Instructions</b> · {esc(trip[instructions_key])}', "small")]
        cell = Table([[content]], colWidths=[CONTENT_W / 2 - 5 * mm])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("LINEBEFORE", (0, 0), (0, -1), 2.5, color),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ]))
        cells.append(cell)
    row = Table([cells], colWidths=[CONTENT_W / 2] * 2)
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def _chapter(number, title):
    return [p(number, "chapter"), section(title)]


def _money_composition(amount, currency):
    table = Table([
        [p("TOTAL BOOKING VALUE", "label"), p(usd(amount), "hero_amount")],
        [p("Pricing preserved at invoice issue", "small"), p(esc(currency), "small_r")],
    ], colWidths=[CONTENT_W * .55, CONTENT_W * .45])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("LINEBEFORE", (0, 0), (0, -1), 3, ORANGE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, 0), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, 0), 2 * mm),
        ("TOPPADDING", (0, 1), (-1, -1), 0), ("BOTTOMPADDING", (0, 1), (-1, -1), 4 * mm),
    ]))
    return table


def render_invoice_pdf(snap: dict, logo: str | None = None) -> bytes:
    """Render the customer invoice as a four-part editorial document."""
    site, cust, trip = snap["site"], snap["customer"], snap["trip"]
    title = "Revised invoice" if snap.get("revision_number") else "Booking invoice"
    meta = [("Invoice no.", snap["invoice_number"]), ("Issue date", snap["issue_date"]),
            ("Booking ref.", snap["booking_reference"])]
    if snap.get("revision_number"):
        meta.append(("Revision of", snap.get("supersedes_number") or "—"))

    # PAGE 01 · Identity, customer and total.
    story = [brand_header(site, "", meta, logo), Spacer(1, 2 * mm),
             p("01  /  FINANCIAL DOCUMENT", "chapter"), p("BOOKING<br/>INVOICE", "invoice_cover"),
             chips_row([
                 ("Booking status", snap.get("booking_status", ""), _status_tone(snap.get("booking_status", ""))),
                 ("Payment status", snap.get("payment_status", ""), _status_tone(snap.get("payment_status", ""))),
             ], gap=9 * mm), Spacer(1, 4 * mm)]
    story += _chapter("A", "A note for the traveller")
    customer_fields = [("Full name", cust.get("full_name")), ("Email", cust.get("email")),
                       ("Phone", cust.get("phone"))]
    if cust.get("nationality"):
        customer_fields.append(("Nationality", cust["nationality"]))
    story.append(info_grid(customer_fields))
    story.append(Spacer(1, 4 * mm))
    story += _chapter("B", "The vehicle")
    car_image = fitted_image(image_reader(trip.get("vehicle_image")), 60 * mm, 38 * mm)
    vehicle = [p(esc(trip.get("vehicle") or "Vehicle"), "value_b"),
               p(f'{trip.get("rental_days", "—")} rental day(s)', "body"),
               p(f'{usd(trip.get("daily_rate"))} per day', "small")]
    vehicle_table = Table([[car_image, vehicle]] if car_image else [[vehicle]],
                          colWidths=[64 * mm, CONTENT_W - 64 * mm] if car_image else [CONTENT_W])
    vehicle_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), .7, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    story += [vehicle_table, Spacer(1, 5 * mm), _money_composition(snap.get("total_amount"), snap.get("currency", "USD"))]
    if snap.get("revision_reason"):
        story += [Spacer(1, 3 * mm), p(f'<b>Revision note</b> · {esc(snap["revision_reason"])}', "small")]

    # PAGE 02 · The rental experience and supplied flight details.
    story += [PageBreak(), brand_header(site, "Your journey", meta, logo),
              p("02  /  YOUR JOURNEY", "chapter"), p("YOUR JOURNEY, BEAUTIFULLY ARRANGED.", "editorial"),
              Spacer(1, 2 * mm)]
    story += _chapter("A", "Vehicle & rental dates")
    story.append(info_grid([
        ("Vehicle", trip.get("vehicle")), ("Rental duration", f'{trip.get("rental_days", "—")} day(s)'),
        ("Daily rental rate", usd(trip.get("daily_rate"))),
        ("Pickup", trip.get("pickup_datetime")), ("Return", trip.get("return_datetime")),
    ]))
    story += [Spacer(1, 3 * mm), RouteDivider(), *_chapter("B", "Pickup to return"), _pickup_return(trip)]
    if snap.get("flight"):
        flight = snap["flight"]
        flight_pairs = [(label, value) for label, value in (
            ("Airline / flight", flight.get("summary")), ("Arrival", flight.get("arrival")),
            ("Airport", flight.get("airport")), ("Instructions", flight.get("notes")),
        ) if value]
        story += [Spacer(1, 4 * mm), *_chapter("C", "Arrival information"), info_grid(flight_pairs)]

    # PAGE 03 · The booking's authoritative saved price lines and payment snapshot.
    story += [PageBreak(), brand_header(site, "Financial details", meta, logo),
              p("03  /  FINANCIAL RECORD", "chapter"), p("YOUR BOOKING, CLEARLY ACCOUNTED FOR.", "editorial"),
              Spacer(1, 2 * mm), *_chapter("A", "Itemized charges")]
    rows = [[item.get("description", ""), str(item.get("quantity", 1)), usd(item.get("unit_price")),
             usd(item.get("total_price"))] for item in snap.get("items", [])]
    totals = [("Subtotal", usd(snap.get("subtotal")), False)]
    if Decimal(str(snap.get("discount_amount") or "0")):
        totals.append(("Discount", f'-{usd(snap["discount_amount"])}', False))
    if Decimal(str(snap.get("tax_amount") or "0")):
        totals.append((f'{snap.get("tax_label") or "Tax"} ({snap.get("tax_rate")}%)', usd(snap["tax_amount"]), False))
    totals.append((f'Grand total · {snap.get("currency", "USD")}', usd(snap.get("total_amount")), True))
    story.append(line_items(["Description", "Quantity", "Unit price", "Amount"], rows,
                            [100 * mm, 18 * mm, 31 * mm, 31 * mm], totals))
    story += [Spacer(1, 4 * mm), *_chapter("B", "Payment record"), info_grid([
        ("Payment method", snap.get("payment_method") or "—"),
        ("Payment status at issue", snap.get("payment_status") or "—"),
        ("Amount paid at issue", usd(snap.get("amount_paid"))),
        ("Outstanding balance at issue", usd(snap.get("balance_due"))),
    ])]
    if snap.get("payment_method_code") == "MANUAL":
        story += [Spacer(1, 3 * mm), p("Manual payments are subject to verification. A separate receipt is issued only after payment is verified.", "small")]
        if snap.get("payment_instructions"):
            story.append(p(esc(snap["payment_instructions"]).replace("\n", "<br/>"), "small"))
    if any("permit" in str(item.get("description", "")).lower() for item in snap.get("items", [])):
        story += [Spacer(1, 3 * mm), p("Driving permit arrangement is assistance only and does not guarantee permit approval.", "small")]

    # PAGE 04 · Terms and a restrained brand signature.
    story += [PageBreak(), brand_header(site, "Final details", meta, logo),
              p("04  /  BEFORE YOU SET OFF", "chapter"), p("IMPORTANT RENTAL INFORMATION.", "editorial"),
              Spacer(1, 5 * mm)]
    if snap.get("terms"):
        story.append(KeepTogether([section("Booking conditions"),
                                   p(esc(snap["terms"]).replace("\n", "<br/>"), "body")]))
    if snap.get("payment_instructions") and snap.get("payment_method_code") == "MANUAL":
        story += [Spacer(1, 5 * mm), section("Payment instructions"),
                  p(esc(snap["payment_instructions"]).replace("\n", "<br/>"), "body")]
    if snap.get("trip", {}).get("pickup_instructions") or snap.get("trip", {}).get("return_instructions"):
        story += [Spacer(1, 5 * mm), section("Your instructions")]
        for label, key in (("Pickup", "pickup_instructions"), ("Return", "return_instructions")):
            if trip.get(key):
                story.append(p(f"<b>{label}</b> · {esc(trip[key])}", "body"))
    story += [Spacer(1, 10 * mm), p("This is a booking invoice and is not necessarily proof of payment.", "small"),
              Spacer(1, 14 * mm), p("RAFIKI CAR HIRE", "brand"), p("DRIVE ZANZIBAR WITH CONFIDENCE.", "tagline")]
    footer = " · ".join(x for x in (site.get("business_phone"), site.get("business_email"), site.get("website")) if x)
    return build_pdf(story, title=f'Invoice {snap["invoice_number"]}', author=site["business_name"],
                     footer=footer, footer_note="Thank you for choosing Rafiki Car Hire · Drive Zanzibar with Confidence.")
