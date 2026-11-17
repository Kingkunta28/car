from reportlab.lib.units import mm
from reportlab.platypus import Spacer

from apps.core.pdf import brand_header, build_pdf, info_grid, line_items, p


def usd(v) -> str:
    return f"${float(v or 0):,.2f}"


def render_receipt_pdf(snap: dict, logo: str | None = None) -> bytes:
    meta = [("Receipt no.", snap["receipt_number"]), ("Date", snap["issue_date"]),
            ("Booking ref.", snap["booking_reference"]), ("Payment ref.", snap["payment_reference"])]
    story = [brand_header(snap["site"], "Payment receipt", meta, logo), Spacer(1, 6 * mm)]
    story.append(p("Received from", "h2"))
    story.append(info_grid([("Customer", snap["customer"]["full_name"]), ("Email", snap["customer"]["email"]),
                            ("Vehicle", snap["vehicle"]), ("Payment method", f'{snap["method"]} — {snap["channel"]}'),
                            ("Transaction reference", snap.get("transaction_reference") or "—")]))
    story.append(p("Payment", "h2"))
    story.append(line_items(
        ["Description", "Amount"], [[f'Payment towards booking {snap["booking_reference"]}', usd(snap["amount"])]],
        [140 * mm, 40 * mm],
        [("Booking total", usd(snap["booking_total"]), False), ("Total paid to date", usd(snap["total_paid"]), False),
         (f'Balance due ({snap["currency"]})', usd(snap["balance"]), True)],
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(p("This receipt confirms a verified payment. It is not an invoice.", "small"))
    return build_pdf(story, title=f'Receipt {snap["receipt_number"]}', author=snap["site"]["business_name"],
                     footer=snap.get("footer") or "")
