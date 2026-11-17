from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Spacer

from apps.core.pdf import brand_header, build_pdf, esc, info_grid, line_items, p


def usd(value) -> str:
    return f"${float(value):,.2f}" if value not in (None, "") else "$0.00"


def render_invoice_pdf(snap: dict, logo: str | None = None) -> bytes:
    """Render an invoice purely from its snapshot dict."""
    site, cust, trip = snap["site"], snap["customer"], snap["trip"]
    title = "Revised invoice" if snap.get("revision_number") else "Invoice"
    meta = [
        ("Invoice no.", snap["invoice_number"]),
        ("Booking ref.", snap["booking_reference"]),
        ("Issue date", snap["issue_date"]),
        ("Currency", snap["currency"]),
    ]
    if snap.get("revision_number"):
        meta.append(("Revision of", snap.get("supersedes_number") or "—"))

    story = [brand_header(site, title, meta, logo), Spacer(1, 6 * mm)]

    story.append(p("Billed to", "h2"))
    story.append(info_grid([
        ("Customer", cust["full_name"]), ("Email", cust["email"]),
        ("Phone", cust["phone"]), ("Nationality", cust.get("nationality") or "—"),
    ]))

    story.append(p("Rental details", "h2"))
    story.append(info_grid([
        ("Vehicle", trip["vehicle"]), ("Rental duration", f'{trip["rental_days"]} day(s)'),
        ("Pickup", trip["pickup_datetime"]), ("Return", trip["return_datetime"]),
        ("Pickup location", trip["pickup_location"]), ("Return location", trip["return_location"]),
        ("Pickup address", trip["pickup_address"]), ("Return address", trip["return_address"]),
    ]))
    if snap.get("flight"):
        f = snap["flight"]
        story.append(info_grid([("Flight", f.get("summary", "")), ("Arrival", f.get("arrival", ""))]))

    story.append(p("Charges", "h2"))
    rows = [[i["description"], str(i["quantity"]), usd(i["unit_price"]), usd(i["total_price"])]
            for i in snap["items"]]
    totals = [("Subtotal", usd(snap["subtotal"]), False)]
    if float(snap.get("tax_amount") or 0):
        totals.append((f'{snap.get("tax_label") or "Tax"} ({snap.get("tax_rate")}%)', usd(snap["tax_amount"]), False))
    totals.append((f'Grand total ({snap["currency"]})', usd(snap["total_amount"]), True))
    story.append(line_items(["Description", "Qty", "Unit price", "Amount"], rows,
                            [100 * mm, 18 * mm, 31 * mm, 31 * mm], totals))

    story.append(Spacer(1, 5 * mm))
    story.append(info_grid([
        ("Payment method", snap["payment_method"]), ("Payment status (at issue)", snap["payment_status"]),
        ("Booking status (at issue)", snap["booking_status"]), ("Amount due", usd(snap["total_amount"])),
    ], cols=4))
    if snap.get("payment_instructions") and snap.get("payment_method_code") == "MANUAL":
        story.append(KeepTogether([p("Payment instructions", "h2"),
                                   p(esc(snap["payment_instructions"]).replace("\n", "<br/>"))]))
    if snap.get("revision_reason"):
        story.append(KeepTogether([p("Reason for revision", "h2"), p(esc(snap["revision_reason"]))]))
    story.append(KeepTogether([p("Important terms &amp; notes", "h2"),
                               p(esc(snap.get("terms", "")).replace("\n", "<br/>"), "small")]))
    return build_pdf(story, title=f'Invoice {snap["invoice_number"]}', author=site["business_name"],
                     footer=snap.get("footer") or "")
