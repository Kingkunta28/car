"""Rafiki Car Hire — PDF design system (ReportLab, server-side).

Every branded document (invoice, receipt, booking confirmation, reports) is built
from these primitives so they share one visual language:

* Brand palette and embedded fonts (Inter for text, Outfit for headings)
* A page template with an orange top rule and a footer showing contact details
  and "Page X of Y"
* Components: header, status chips, section titles, panels, key/value grids,
  tables, totals block, images fitted without distortion
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# --------------------------------------------------------------------------
# Brand tokens
# --------------------------------------------------------------------------
NAVY = colors.HexColor("#101C35")
ORANGE = colors.HexColor("#E98228")
ORANGE_DARK = colors.HexColor("#A95417")
WHITE = colors.white
LIGHT = colors.HexColor("#F8F6F1")
TEXT = colors.HexColor("#222936")
MUTED = colors.HexColor("#858B95")
BORDER = colors.HexColor("#E4E0D7")
GREEN = colors.HexColor("#0F7B4F")
GREEN_BG = colors.HexColor("#E7F6EE")
AMBER = colors.HexColor("#9A5B06")
AMBER_BG = colors.HexColor("#FFF4E0")
RED = colors.HexColor("#B42318")
RED_BG = colors.HexColor("#FDECEA")
BLUE = colors.HexColor("#1D4E89")
BLUE_BG = colors.HexColor("#E8F0FB")
SLATE_BG = colors.HexColor("#EEF1F5")
GRAY = MUTED  # backwards-compatible alias

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

# --------------------------------------------------------------------------
# Fonts (embedded; graceful fallback to Helvetica)
# --------------------------------------------------------------------------
_FONT_DIR = Path(__file__).resolve().parent / "fonts"
F = {"regular": "Helvetica", "medium": "Helvetica", "semibold": "Helvetica-Bold", "bold": "Helvetica-Bold",
     "display": "Helvetica-Bold", "display_xb": "Helvetica-Bold"}


def _register_fonts():
    files = {"Inter": "Inter-400.ttf", "Inter-Medium": "Inter-500.ttf", "Inter-SemiBold": "Inter-600.ttf",
             "Inter-Bold": "Inter-700.ttf", "Outfit-SemiBold": "Outfit-600.ttf", "Outfit-Bold": "Outfit-700.ttf",
             "Outfit-ExtraBold": "Outfit-800.ttf"}
    try:
        for name, fname in files.items():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(_FONT_DIR / fname)))
        pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Bold", italic="Inter", boldItalic="Inter-Bold")
        F.update(regular="Inter", medium="Inter-Medium", semibold="Inter-SemiBold", bold="Inter-Bold",
                 display="Outfit-Bold", display_xb="Outfit-ExtraBold")
    except Exception:  # missing font files — keep Helvetica
        pass


_register_fonts()


def _style(name, **kw):
    base = dict(fontName=F["regular"], fontSize=9, leading=13, textColor=TEXT)
    base.update(kw)
    return ParagraphStyle(name, **base)


STYLES = {
    "body": _style("body"),
    "body_r": _style("body_r", alignment=TA_RIGHT),
    "small": _style("small", fontSize=7.6, leading=10.5, textColor=MUTED),
    "small_r": _style("small_r", fontSize=7.6, leading=10.5, textColor=MUTED, alignment=TA_RIGHT),
    "label": _style("label", fontName=F["semibold"], fontSize=6.8, leading=9, textColor=MUTED),
    "label_r": _style("label_r", fontName=F["semibold"], fontSize=6.8, leading=9, textColor=MUTED, alignment=TA_RIGHT),
    "value": _style("value", fontName=F["medium"], fontSize=9.4, leading=13, textColor=TEXT),
    "value_b": _style("value_b", fontName=F["semibold"], fontSize=10, leading=13.5, textColor=NAVY),
    "value_r": _style("value_r", fontName=F["semibold"], fontSize=9, leading=12.5, textColor=NAVY, alignment=TA_RIGHT),
    "title": _style("title", fontName=F["display_xb"], fontSize=27, leading=29, textColor=NAVY, alignment=TA_RIGHT),
    "title_l": _style("title_l", fontName=F["display_xb"], fontSize=22, leading=25, textColor=NAVY),
    "invoice_cover": _style("invoice_cover", fontName="Times-Bold", fontSize=34, leading=35, textColor=NAVY),
    "editorial": _style("editorial", fontName="Times-Bold", fontSize=24, leading=28, textColor=NAVY),
    "chapter": _style("chapter", fontName=F["semibold"], fontSize=8, leading=10, textColor=ORANGE_DARK),
    "reference": _style("reference", fontName="Courier-Bold", fontSize=10, leading=13, textColor=NAVY),
    "hero_amount": _style("hero_amount", fontName=F["display_xb"], fontSize=30, leading=33,
                           textColor=NAVY, alignment=TA_RIGHT),
    "brand": _style("brand", fontName=F["display"], fontSize=15, leading=18, textColor=NAVY),
    "tagline": _style("tagline", fontName=F["medium"], fontSize=8.2, leading=11, textColor=ORANGE_DARK),
    "section": _style("section", fontName=F["display"], fontSize=10.5, leading=13, textColor=NAVY),
    "cell": _style("cell", fontSize=8.8, leading=12),
    "cell_sub": _style("cell_sub", fontSize=7.4, leading=10, textColor=MUTED),
    "cell_r": _style("cell_r", fontSize=8.8, leading=12, alignment=TA_RIGHT),
    "cell_rb": _style("cell_rb", fontName=F["semibold"], fontSize=8.8, leading=12, alignment=TA_RIGHT, textColor=NAVY),
    "th": _style("th", fontName=F["semibold"], fontSize=7, leading=9, textColor=MUTED),
    "th_r": _style("th_r", fontName=F["semibold"], fontSize=7, leading=9, textColor=MUTED, alignment=TA_RIGHT),
    "center": _style("center", alignment=TA_CENTER),
    # legacy names used by older callers
    "h1": _style("h1", fontName=F["display_xb"], fontSize=20, leading=24, textColor=NAVY),
    "h2": _style("h2", fontName=F["display"], fontSize=10.5, leading=14, textColor=NAVY, spaceBefore=10, spaceAfter=4),
    "right": _style("right_legacy", alignment=TA_RIGHT),
}


def esc(value) -> str:
    return (str(value if value is not None else "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def p(text, style="body"):
    return Paragraph(text, STYLES[style] if isinstance(style, str) else style)


def money(v) -> str:
    try:
        d = Decimal(str(v or 0))
    except Exception:
        d = Decimal("0")
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


# --------------------------------------------------------------------------
# Images (fit inside a box, never stretched)
# --------------------------------------------------------------------------
def image_reader(source) -> ImageReader | None:
    """Open an image from a filesystem path or a storage name (local or S3)."""
    if not source:
        return None
    try:
        path = Path(str(source))
        if path.is_absolute() and path.exists():
            return ImageReader(str(path))
        from django.core.files.storage import default_storage

        with default_storage.open(str(source), "rb") as fh:
            return ImageReader(BytesIO(fh.read()))
    except Exception:
        return None


def fitted_image(reader: ImageReader | None, max_w, max_h):
    if reader is None:
        return None
    iw, ih = reader.getSize()
    scale = min(max_w / iw, max_h / ih)
    # Platypus Image accepts paths or encoded image streams, not ImageReader
    # instances. Re-encode a downsampled copy so PDFs work with real uploads
    # and do not embed unnecessarily large source photographs.
    source = reader._image
    target_size = (max(1, round(max_w / 72 * 144)), max(1, round(max_h / 72 * 144)))
    source.thumbnail(target_size)
    has_alpha = "A" in source.getbands() or "transparency" in source.info
    image_buffer = BytesIO()
    if has_alpha:
        source.save(image_buffer, format="PNG", optimize=True)
    else:
        source.convert("RGB").save(image_buffer, format="JPEG", quality=86, optimize=True)
    image_buffer.seek(0)
    img = Image(image_buffer, width=iw * scale, height=ih * scale)
    img._restrictSize(max_w, max_h)
    return img


# --------------------------------------------------------------------------
# Small flowables
# --------------------------------------------------------------------------
TONES = {
    "green": (GREEN_BG, GREEN), "amber": (AMBER_BG, AMBER), "red": (RED_BG, RED), "blue": (BLUE_BG, BLUE),
    "slate": (SLATE_BG, colors.HexColor("#3B4658")), "navy": (NAVY, WHITE), "orange": (ORANGE, NAVY),
}
STATUS_TONE = {
    "PENDING_CONFIRMATION": "amber", "CONFIRMED": "green", "COMPLETED": "navy", "CANCELLED": "red",
    "REJECTED": "red", "EXPIRED": "slate", "UNPAID": "red", "PENDING_VERIFICATION": "amber",
    "PARTIALLY_PAID": "blue", "PAID": "green", "PARTIALLY_REFUNDED": "blue", "REFUNDED": "slate",
}


class Chip(Flowable):
    """A rounded status pill: small label above, bold value inside the pill."""

    def __init__(self, label, text, tone="slate"):
        super().__init__()
        self.label, self.text = label.upper(), text.upper()
        self.bg, self.fg = TONES.get(tone, TONES["slate"])
        self.tw = pdfmetrics.stringWidth(self.text, F["bold"], 7.4)
        self.lw = pdfmetrics.stringWidth(self.label, F["semibold"], 6.4)
        self.width = max(self.tw + 18, self.lw)
        self.height = 25

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFont(F["semibold"], 6.4)
        c.setFillColor(MUTED)
        c.drawString(0, 19, self.label)
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.tw + 18, 14.5, 7.25, stroke=0, fill=1)
        c.setFillColor(self.fg)
        c.circle(7.5, 7.25, 2, stroke=0, fill=1)
        c.setFont(F["bold"], 7.4)
        c.drawString(12.5, 4.6, self.text)


def chips_row(items, gap=8 * mm):
    """items: list of (label, text, tone)."""
    flows = [Chip(*it) for it in items]
    t = Table([flows], colWidths=[f.width + gap for f in flows], hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    return t


class SectionTitle(Flowable):
    """Orange tick + heading + hairline to the right edge."""

    def __init__(self, text, width=None, space_before=7 * mm, space_after=3 * mm):
        super().__init__()
        self.text = text.upper()
        self.w = width or CONTENT_W
        self.sb, self.sa = space_before, space_after

    def wrap(self, aw, ah):
        self.w = min(self.w, aw)
        return self.w, 12 + self.sb + self.sa

    def draw(self):
        c = self.canv
        y = self.sa
        c.setFillColor(ORANGE)
        c.rect(0, y + 1, 3.2, 8.5, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.setFont(F["display"], 9.2)
        tw = pdfmetrics.stringWidth(self.text, F["display"], 9.2) + 0.9 * len(self.text)
        c.drawString(8, y + 2, " ".join([]) or "")
        tx = c.beginText(8, y + 2)
        tx.setFont(F["display"], 9.2)
        tx.setCharSpace(0.9)
        tx.textOut(self.text)
        c.drawText(tx)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.6)
        c.line(8 + tw + 8, y + 5.5, self.w, y + 5.5)


def section(text, **kw):
    return SectionTitle(text, **kw)


def panel(rows, col_widths, *, bg=LIGHT, pad=4 * mm, radius=6, border=None, valign="TOP", extra=None):
    """A soft rounded block (light grey by default) holding a grid of flowables."""
    t = Table(rows, colWidths=col_widths)
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("VALIGN", (0, 0), (-1, -1), valign),
        ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad * 0.75), ("BOTTOMPADDING", (0, 0), (-1, -1), pad * 0.75),
        ("ROUNDEDCORNERS", [radius] * 4),
    ]
    if border:
        style.append(("BOX", (0, 0), (-1, -1), 0.7, border))
    t.setStyle(TableStyle(style + (extra or [])))
    return t


def kv(label, value, value_style="value", label_style="label"):
    return [p(esc(label).upper(), label_style), p(esc(value) if value not in (None, "") else "—", value_style)]


def kv_grid(pairs, cols=2, width=CONTENT_W, pad=4 * mm, bg=LIGHT):
    cells, row, rows = [], [], []
    for label, value in pairs:
        row.append(kv(label, value))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        row += [""] * (cols - len(row))
        rows.append(row)
    return panel(rows, [width / cols] * cols, pad=pad, bg=bg)


def info_grid(pairs, cols=2):
    """Compatibility wrapper for invoice and receipt document layouts."""
    return kv_grid(pairs, cols=cols)


def data_table(headers, rows, col_widths, *, align=None, zebra=True, total_row=None, font_size=None):
    """Clean table: muted header labels, hairline separators, optional zebra striping."""
    align = align or ["L"] + ["R"] * (len(headers) - 1)
    head = [p(esc(h).upper(), "th_r" if a == "R" else "th") for h, a in zip(headers, align)]
    body = []
    for r in rows:
        body.append([c if isinstance(c, Flowable) else p(esc(c), "cell_r" if a == "R" else "cell") for c, a in zip(r, align)])
    data = [head] + body
    if total_row:
        data.append([c if isinstance(c, Flowable) else p(f"<b>{esc(c)}</b>", "cell_rb" if a == "R" else "cell") for c, a in zip(total_row, align)])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if zebra:
        for i in range(1, len(body) + 1):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
    if total_row:
        style += [("BACKGROUND", (0, -1), (-1, -1), LIGHT), ("LINEABOVE", (0, -1), (-1, -1), 0.9, NAVY)]
    t.setStyle(TableStyle(style))
    return t


def totals_block(lines, grand_label, grand_value, width=82 * mm, note=None):
    """Right-aligned totals: muted lines, then a navy grand-total bar."""
    rows = [[p(esc(l), "small"), p(esc(v), "value_r")] for l, v in lines]
    t1 = Table(rows, colWidths=[width * 0.58, width * 0.42]) if rows else None
    if t1:
        t1.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                                ("LINEBELOW", (0, -1), (-1, -1), 0.4, BORDER)]))
    grand = Table([[p(f'<font color="#FFFFFF">{esc(grand_label).upper()}</font>', _style("gl", fontName=F["semibold"], fontSize=7.6, textColor=WHITE, leading=10)),
                    p(f'<font color="#FFFFFF">{esc(grand_value)}</font>', _style("gv", fontName=F["display_xb"], fontSize=19, leading=22, textColor=WHITE, alignment=TA_RIGHT))]],
                  colWidths=[width * 0.45, width * 0.55])
    grand.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                               ("TOPPADDING", (0, 0), (-1, -1), 3.6 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6 * mm),
                               ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                               ("LINEBEFORE", (0, 0), (0, 0), 3, ORANGE)]))
    parts = [x for x in (t1, Spacer(1, 2 * mm) if t1 else None, grand) if x is not None]
    if note:
        parts += [Spacer(1, 1.6 * mm), p(note, "small_r")]
    outer = Table([[parts]], colWidths=[width], hAlign="RIGHT")
    outer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return outer


def line_items(headers, rows, col_widths, totals):
    """Render a line item table followed by its right-aligned totals."""
    table_width = sum(col_widths)
    scale = min(1, CONTENT_W / table_width) if table_width else 1
    col_widths = [width * scale for width in col_widths]
    table = data_table(headers, rows, col_widths)
    ordinary = [(label, value) for label, value, is_grand in totals if not is_grand]
    grand = next(((label, value) for label, value, is_grand in totals if is_grand), None)
    if grand is None:
        return table
    total = totals_block(ordinary, grand[0], grand[1], width=min(82 * mm, sum(col_widths)))
    wrapper = Table([[table], [total]], colWidths=[sum(col_widths)])
    wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def brand_header(site: dict, title: str, meta_rows: list[tuple[str, str]], logo=None, subtitle: str | None = None):
    """Two-column document header: logo + business block | document title + reference meta."""
    logo_img = fitted_image(image_reader(logo), 34 * mm, 24 * mm) if logo else None
    contact = [x for x in (site.get("business_phone"), site.get("business_email")) if x]
    biz = [p(esc(site.get("business_name") or "Rafiki Car Hire"), "brand"),
           p(esc(site.get("tagline") or "Drive Zanzibar with Confidence."), "tagline"),
           Spacer(1, 1.5 * mm),
           p(esc(site.get("business_address") or "Abeid Amani Karume International Airport, Zanzibar, Tanzania"), "small"),
           p(esc("Abeid Amani Karume International Airport, Zanzibar, Tanzania")
             if "Tanzania" not in (site.get("business_address") or "") else "", "small")]
    if contact:
        biz.append(p(" · ".join(esc(c) for c in contact), "small"))
    if site.get("website"):
        biz.append(p(esc(site["website"]), "small"))
    left = Table([[logo_img, biz]] if logo_img else [[biz]], colWidths=[37 * mm, 58 * mm] if logo_img else [95 * mm])
    left.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    meta = Table([[p(esc(k).upper(), "label_r"), p(esc(v), "value_r")] for k, v in meta_rows],
                 colWidths=[30 * mm, 50 * mm], hAlign="RIGHT")
    meta.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1.4), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    right = [p(esc(title).upper(), "title")]
    if subtitle:
        right.append(p(esc(subtitle), "small_r"))
    right += [Spacer(1, 3 * mm), meta]
    t = Table([[left, right]], colWidths=[CONTENT_W * 0.54, CONTENT_W * 0.46])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm), ("LINEBELOW", (0, 0), (-1, 0), 0.8, BORDER)]))
    return t


def note_box(title, body_html, tone="slate"):
    bg, fg = {"amber": (AMBER_BG, AMBER), "slate": (LIGHT, NAVY), "blue": (BLUE_BG, BLUE)}.get(tone, (LIGHT, NAVY))
    return panel([[[p(f'<font name="{F["semibold"]}" color="{fg.hexval()[2:] and "#" + fg.hexval()[2:]}">{esc(title)}</font>', "body"),
                    Spacer(1, 1 * mm), p(body_html, "small")]]], [CONTENT_W], bg=bg, pad=4 * mm,
                 extra=[("LINEBEFORE", (0, 0), (0, -1), 2.4, fg)])


# --------------------------------------------------------------------------
# Page template: "Page X of Y" footer with contact details
# --------------------------------------------------------------------------
def _numbered_canvas_factory(footer_left: str, footer_note: str, landscape_mode: bool, stamp=None):
    pagesize = landscape(A4) if landscape_mode else A4

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state in self._saved:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total):
            w, h = pagesize
            self.saveState()
            # Orange top rule + navy hairline
            self.setFillColor(ORANGE)
            self.rect(0, h - 3.2, w, 3.2, stroke=0, fill=1)
            # A small printer-registration cross is the document's recurring
            # editorial mark, kept in the top-right margin clear of content.
            self.setStrokeColor(ORANGE)
            self.setLineWidth(0.55)
            mark_x, mark_y = w - MARGIN_X, h - 9 * mm
            self.line(mark_x - 2 * mm, mark_y, mark_x + 2 * mm, mark_y)
            self.line(mark_x, mark_y - 2 * mm, mark_x, mark_y + 2 * mm)
            # Footer
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.6)
            self.line(MARGIN_X, 15 * mm, w - MARGIN_X, 15 * mm)
            self.setFont(F["regular"], 6.9)
            self.setFillColor(MUTED)
            if footer_note:
                self.drawString(MARGIN_X, 10.6 * mm, footer_note[:190])
            self.setFillColor(NAVY)
            self.setFont(F["semibold"], 6.9)
            self.drawString(MARGIN_X, 7 * mm, footer_left[:170])
            self.setFillColor(MUTED)
            self.setFont(F["regular"], 6.9)
            self.drawRightString(w - MARGIN_X, 7 * mm, f"Page {self._pageNumber} of {total}")
            if stamp and self._pageNumber == 1:
                stamp(self, w, h)
            self.restoreState()

    return NumberedCanvas


def build_pdf(story, *, title: str, author: str, footer: str = "", footer_note: str = "", landscape_mode=False,
              stamp=None, site: dict | None = None) -> bytes:
    """Render a story to PDF bytes with the branded page template."""
    buf = BytesIO()
    pagesize = landscape(A4) if landscape_mode else A4
    if site and not footer:
        bits = [site.get("business_name") or "Rafiki Car Hire",
                "Abeid Amani Karume International Airport, Zanzibar, Tanzania"]
        bits += [x for x in (site.get("business_phone"), site.get("business_email"), site.get("website")) if x]
        footer = "  ·  ".join(bits)
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                            topMargin=14 * mm, bottomMargin=20 * mm, title=title, author=author, creator=author,
                            subject=title)
    doc.build(story, canvasmaker=_numbered_canvas_factory(footer or author, footer_note, landscape_mode, stamp))
    return buf.getvalue()


def draw_stamp(text, color=GREEN, x=None, y=None, angle=14):
    """Return a callback that draws a rotated rubber-stamp style mark on page 1."""

    def _stamp(c, w, h):
        c.saveState()
        c.translate(x if x is not None else w - 62 * mm, y if y is not None else h - 94 * mm)
        c.rotate(angle)
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(2)
        tw = pdfmetrics.stringWidth(text, F["display_xb"], 20)
        c.setFillAlpha(0.9)
        c.roundRect(-tw / 2 - 9, -10, tw + 18, 30, 5, stroke=1, fill=0)
        c.setFont(F["display_xb"], 20)
        c.drawCentredString(0, -1, text)
        c.restoreState()

    return _stamp


# --------------------------------------------------------------------------
# Site helpers
# --------------------------------------------------------------------------
def _public_website() -> str:
    url = getattr(settings, "FRONTEND_URL", "") or ""
    return "" if ("localhost" in url or "127.0.0.1" in url or not url) else url.replace("https://", "").replace("http://", "")


def site_dict(site) -> dict:
    return {
        "business_name": site.business_name, "tagline": site.tagline, "business_email": site.business_email,
        "business_phone": site.business_phone, "business_address": site.business_address,
        "whatsapp_number": site.whatsapp_number, "website": _public_website(),
    }


def logo_path(site) -> str | None:
    """Storage name of the uploaded logo (resolved through storage, so S3 works too)."""
    try:
        return site.logo.name if site.logo else None
    except Exception:
        return None


__all__ = [
    "NAVY", "ORANGE", "LIGHT", "TEXT", "MUTED", "BORDER", "GRAY", "F", "STYLES", "esc", "p", "money", "brand_header",
    "chips_row", "section", "panel", "kv", "kv_grid", "info_grid", "data_table", "line_items", "totals_block", "note_box", "fitted_image",
    "image_reader", "build_pdf", "draw_stamp", "site_dict", "logo_path", "STATUS_TONE", "CONTENT_W", "KeepTogether",
    "Spacer", "Table", "TableStyle", "mm", "TA_LEFT",
]
