"""Branded PDF building blocks (ReportLab — pure Python, no system libraries)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#0B1F3A")
ORANGE = colors.HexColor("#F28C28")
GRAY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#E5E7EB")

_base = getSampleStyleSheet()
STYLES = {
    "body": ParagraphStyle("body", parent=_base["Normal"], fontName="Helvetica", fontSize=9, leading=12.5,
                           textColor=colors.HexColor("#111827")),
    "small": ParagraphStyle("small", parent=_base["Normal"], fontName="Helvetica", fontSize=7.5, leading=10,
                            textColor=GRAY),
    "label": ParagraphStyle("label", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                            textColor=GRAY),
    "h1": ParagraphStyle("h1", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24,
                         textColor=NAVY, spaceAfter=0),
    "h2": ParagraphStyle("h2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                         textColor=NAVY, spaceBefore=10, spaceAfter=4),
    "brand": ParagraphStyle("brand", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=19,
                            textColor=NAVY),
    "right": ParagraphStyle("right", parent=_base["Normal"], fontName="Helvetica", fontSize=9, leading=12.5,
                            alignment=TA_RIGHT),
}


def esc(value) -> str:
    return (str(value if value is not None else "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def brand_header(site: dict, title: str, meta_rows: list[tuple[str, str]], logo_path: str | None = None):
    """Two-column header: brand block left, document title + meta right."""
    if logo_path:
        try:
            logo = Image(logo_path, width=42 * mm, height=16 * mm, kind="proportional")
        except Exception:  # unreadable logo — fall back to wordmark
            logo = None
    else:
        logo = None
    brand = [logo or p(f'{esc(site["business_name"]).upper()}<font color="#F28C28">.</font>', "brand")]
    contact = [site.get("business_address"), site.get("business_phone"), site.get("business_email")]
    brand.append(p("<br/>".join(esc(c) for c in contact if c), "small"))

    meta = [[p(esc(k), "label"), p(f"<b>{esc(v)}</b>", "right")] for k, v in meta_rows]
    meta_table = Table(meta, colWidths=[32 * mm, 48 * mm])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
    right = [p(esc(title).upper(), "h1"), Spacer(1, 3 * mm), meta_table]

    t = Table([[brand, right]], colWidths=[95 * mm, 85 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                           ("LINEBELOW", (0, 0), (-1, 0), 2, ORANGE), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def info_grid(cells: list[tuple[str, str]], cols=2, width=180 * mm):
    """Label/value grid, e.g. customer and trip details."""
    rows, row = [], []
    for label, value in cells:
        row.append([p(esc(label).upper(), "label"), p(esc(value) or "—")])
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        row += [""] * (cols - len(row))
        rows.append(row)
    t = Table(rows, colWidths=[width / cols] * cols)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def line_items(headers: list[str], rows: list[list[str]], col_widths, totals: list[tuple[str, str, bool]]):
    data = [[p(f"<b>{esc(h)}</b>", "label") for h in headers]]
    data += [[p(esc(c)) if i == 0 else p(esc(c), "right") for i, c in enumerate(r)] for r in rows]
    n = len(data)
    for label, value, strong in totals:
        lab = f"<b>{esc(label)}</b>" if strong else esc(label)
        val = f"<b>{esc(value)}</b>" if strong else esc(value)
        data.append([""] * (len(headers) - 2) + [p(lab, "right"), p(val, "right")])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.6, BORDER),
        ("LINEBELOW", (0, 1), (-1, n - 1), 0.4, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if totals:
        style += [("LINEABOVE", (-2, -1), (-1, -1), 1.2, NAVY), ("BACKGROUND", (-2, -1), (-1, -1), LIGHT)]
    t.setStyle(TableStyle(style))
    return t


def build_pdf(story, *, title: str, author: str, footer: str = "", landscape_mode=False) -> bytes:
    buf = BytesIO()
    pagesize = landscape(A4) if landscape_mode else A4

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, pagesize[0], 4 * mm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        if footer:
            canvas.drawString(15 * mm, 8 * mm, footer[:150])
        canvas.drawRightString(pagesize[0] - 15 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm,
                            bottomMargin=16 * mm, title=title, author=author, creator=author)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def site_dict(site) -> dict:
    return {
        "business_name": site.business_name, "business_email": site.business_email,
        "business_phone": site.business_phone, "business_address": site.business_address,
        "whatsapp_number": site.whatsapp_number,
    }


def logo_path(site) -> str | None:
    try:
        return site.logo.path if site.logo else None
    except (NotImplementedError, ValueError):  # remote storage — skip
        return None
