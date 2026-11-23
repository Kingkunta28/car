from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle

from apps.core.pdf import CONTENT_W, LIGHT, BORDER, brand_header, build_pdf, chips_row, esc, info_grid, line_items, logo_path, p, section
from apps.core.models import SiteSettings
from apps.core.pdf import site_dict
from .vehicle_data import booking_vehicle_snapshot


def render_confirmation_pdf(booking) -> bytes:
    """Generate a guest booking confirmation from the saved booking record."""
    site_settings = SiteSettings.load()
    site = site_dict(site_settings)
    vehicle = booking_vehicle_snapshot(booking)
    trip = {
        "vehicle": f"{vehicle.get('name', 'Vehicle')} ({vehicle.get('brand', '')} {vehicle.get('model', '')}{', ' + str(vehicle['year']) if vehicle.get('year') else ''})",
        "pickup": f"{booking.pickup_date:%a %d %b %Y} at {booking.pickup_time:%H:%M}",
        "return": f"{booking.return_date:%a %d %b %Y} at {booking.return_time:%H:%M}",
    }
    meta = [("Booking ref.", booking.booking_reference), ("Created", booking.created_at.strftime("%d %B %Y"))]
    customer_status = "ACCEPTED" if booking.booking_status == "CONFIRMED" else booking.get_booking_status_display()
    story = [brand_header(site, "Booking voucher", meta, logo_path(SiteSettings.load())),
             chips_row([("Booking status", customer_status, "green" if booking.booking_status == "CONFIRMED" else "amber"),
                        ("Payment status", booking.get_payment_status_display(), "green" if booking.payment_status == "PAID" else "amber")]),
             section("Guest"), info_grid([
                 ("Name", booking.customer.full_name), ("Email", booking.customer.email),
                 ("Phone", booking.customer.phone), ("Nationality", booking.customer.nationality or "—"),
             ])]
    story += [section("Vehicle & rental"), info_grid([
        ("Vehicle", trip["vehicle"]), ("Duration", f"{booking.rental_days} day(s)"),
        ("Daily rate", f"${booking.daily_rate:,.2f}"),
        ("Transmission", vehicle.get("transmission_display") or vehicle.get("transmission") or "—"),
    ])]
    def location_card(title, color, location, area, address, when, instructions):
        rows = [p(f'<font color="{color}"><b>{title}</b></font>', "label"),
                p(esc(location + (f" · {area}" if area else "")), "value_b"),
                p(esc(when), "small")]
        if address:
            rows.append(p(esc(address), "small"))
        if instructions:
            rows.append(p(f'<b>Instructions:</b> {esc(instructions)}', "small"))
        card = Table([[rows]], colWidths=[CONTENT_W / 2 - 5 * mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(color)),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        return card
    pickup = location_card("PICKUP", "#F28C28", booking.get_pickup_type_display(), booking.pickup_area,
                           booking.pickup_address, trip["pickup"], booking.pickup_instructions)
    ret = location_card("RETURN", "#101C35", booking.get_return_type_display(), booking.return_area,
                        booking.return_address, trip["return"], booking.return_instructions)
    legs = Table([[pickup, ret]], colWidths=[CONTENT_W / 2] * 2)
    legs.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                              ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story += [section("Pickup & return"), legs]
    flight = getattr(booking, "flight", None)
    if flight and (flight.airline_name or flight.flight_number):
        story += [section("Arrival details"), info_grid([
            ("Flight", f"{flight.airline_name} {flight.flight_number}".strip()),
            ("Arrival", f"{flight.arrival_date or ''} {flight.arrival_time or ''}".strip()),
            ("Airport", flight.arrival_airport or "—"), ("Notes", flight.notes or "—"),
        ])]
    lines = booking.pricing_breakdown.get("lines", [])
    fmt = lambda value: f"${Decimal(str(value or 0)):,.2f}"
    rows = [[line.get("description", ""), str(line.get("quantity", 1)),
             fmt(line.get("unit_price")), fmt(line.get("total"))] for line in lines]
    totals = [("Subtotal", fmt(booking.pricing_breakdown.get("subtotal", booking.grand_total)), False)]
    if booking.tax_amount:
        totals.append(("Tax", f"${booking.tax_amount:,.2f}", False))
    totals.append((f"Grand total ({booking.currency})", f"${booking.grand_total:,.2f}", True))
    story += [section("Price summary"), line_items(["Description", "Qty", "Unit price", "Amount"], rows,
                                                   [100 * mm, 18 * mm, 31 * mm, 31 * mm], totals),
              section("Payment"), info_grid([
                  ("Method", booking.get_payment_method_display()), ("Payment status", booking.get_payment_status_display()),
                  ("Paid", f"${booking.amount_paid:,.2f}"), ("Balance due", f"${booking.balance_due:,.2f}"),
              ]), p("Your booking status is shown above. Payment status is tracked separately.", "small")]
    if site_settings.invoice_terms:
        story += [section("Important rental information"),
                  p(esc(site_settings.invoice_terms).replace("\n", "<br/>"), "small")]
    footer = " · ".join(x for x in (site.get("business_phone"), site.get("business_email"), site.get("website")) if x)
    return build_pdf(story, title=f"Booking voucher {booking.booking_reference}", author=site["business_name"],
                     footer=footer, footer_note="Thank you for choosing Rafiki Car Hire · Drive Zanzibar with Confidence.")
