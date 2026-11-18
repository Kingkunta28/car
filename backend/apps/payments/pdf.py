from reportlab.platypus import Spacer
from reportlab.lib.units import mm

from apps.core.pdf import build_pdf, draw_stamp, info_grid, line_items, p, section
from apps.invoices.pdf import usd
from apps.core.pdf import brand_header


def render_receipt_pdf(snap: dict, logo: str | None = None) -> bytes:
    """Render a receipt from a verified payment's immutable snapshot."""
    meta = [("Receipt no.", snap["receipt_number"]), ("Payment date", snap["issue_date"]),
            ("Booking ref.", snap["booking_reference"]), ("Payment ref.", snap.get("payment_reference", "—"))]
    if snap.get("transaction_reference"):
        meta.append(("Transaction ref.", snap["transaction_reference"]))
    story = [brand_header(snap["site"], "Payment receipt", meta, logo), Spacer(1, 5 * mm)]
    story += [section("Payment received"), info_grid([
        ("Customer", snap["customer"]["full_name"]), ("Email", snap["customer"]["email"]),
        ("Phone", snap["customer"].get("phone")), ("Vehicle", snap.get("vehicle")),
        ("Payment method", snap.get("method")), ("Channel", snap.get("channel")),
        ("Verification", snap.get("verification_source") or "Verified"),
    ])]
    story.append(Spacer(1, 6 * mm))
    story.append(line_items(
        ["Description", "Amount received"],
        [[f'Payment towards booking {snap["booking_reference"]}', usd(snap["amount"])]],
        [140 * mm, 40 * mm],
        [("Booking total", usd(snap["booking_total"]), False),
         ("Total paid to date", usd(snap["total_paid"]), False),
         (f'Balance due ({snap["currency"]})', usd(snap["balance"]), True)],
    ))
    story += [Spacer(1, 5 * mm), p("This receipt confirms the verified payment amount shown above. It is not an invoice.", "small")]
    footer = " · ".join(x for x in (snap["site"].get("business_phone"), snap["site"].get("business_email"),
                                    snap["site"].get("website")) if x)
    return build_pdf(story, title=f'Receipt {snap["receipt_number"]}', author=snap["site"]["business_name"],
                     footer=footer, footer_note="Thank you for choosing Rafiki Car Hire · Drive Zanzibar with Confidence.",
                     stamp=draw_stamp("PAID"))
