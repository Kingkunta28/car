import csv
import io
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from apps.accounts.permissions import ALL_ROLES, FINANCE_ROLES
from apps.core.models import SiteSettings
from apps.core.pdf import BORDER, LIGHT, build_pdf, data_table, esc, fitted_image, image_reader, p, site_dict, logo_path
from apps.core.utils import audit
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services

REPORTS = {"bookings", "revenue", "vehicles", "payments", "outstanding"}


class DashboardView(APIView):
    required_roles = ALL_ROLES

    def get(self, request):
        data = services.dashboard()
        if not request.user.has_role(*FINANCE_ROLES):
            data["revenue"] = None  # staff role does not see revenue figures
        return Response(data)


def _range(params):
    today = timezone.localdate()
    start = parse_date(params.get("date_from") or "") or today.replace(day=1)
    end = parse_date(params.get("date_to") or "") or today
    if end < start:
        raise ValidationError({"date_to": "End date must be after start date."})
    return start, end


def _to_csv(report) -> HttpResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(report["headers"])
    for r in report["rows"]:
        w.writerow([r.get(c, "") for c in report["columns"]])
    for k, v in (report.get("summary") or {}).items():
        w.writerow([])
        w.writerow([k.replace("_", " ").title(), v])
    resp = HttpResponse("﻿" + buf.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{report["slug"]}.csv"'
    return resp


def _to_pdf(report) -> HttpResponse:
    site = SiteSettings.load()
    n = len(report["columns"])
    width = landscape(A4)[0] - 32 * mm
    logo = fitted_image(image_reader(logo_path(site)), 30 * mm, 22 * mm)
    company = [p(esc(site.business_name), "brand"),
               p(esc(site.tagline or "Drive Zanzibar with Confidence"), "tagline"),
               p(esc(site.business_address or "Zanzibar, Tanzania"), "small")]
    contacts = " · ".join(x for x in (site.business_phone, site.business_email) if x)
    if contacts:
        company.append(p(esc(contacts), "small"))
    identity = Table([[logo, company]] if logo else [[company]],
                     colWidths=[34 * mm, 91 * mm] if logo else [125 * mm])
    identity.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    generated = timezone.localtime().strftime("%d %b %Y · %H:%M EAT")
    heading = [p(esc(report["title"]), "title_l"), p(f"Generated {generated}", "small_r")]
    if report.get("period_label"):
        heading.append(p(esc(report["period_label"]), "small_r"))
    head = Table([[identity, heading]], colWidths=[width * .58, width * .42])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
                              ("LINEBELOW", (0, 0), (-1, -1), .8, BORDER)]))
    story = [head, Spacer(1, 4 * mm)]
    summary = report.get("summary") or {}
    if summary:
        cards = []
        pairs = list(summary.items())
        for i in range(0, len(pairs), 2):
            row = []
            for key, value in pairs[i:i + 2]:
                row.append([p(esc(key.replace("_", " ").title()), "label"), p(esc(value), "value_b")])
            if len(row) == 1:
                row.append("")
            cards.append(row)
        metrics = Table(cards, colWidths=[width / 2, width / 2])
        metrics.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                                     ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                     ("BOX", (0, 0), (-1, -1), .5, BORDER),
                                     ("INNERGRID", (0, 0), (-1, -1), .5, BORDER),
                                     ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                                     ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                                     ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm)]))
        story += [metrics, Spacer(1, 5 * mm)]
    numeric = {"total", "confirmed", "completed", "pending", "lost", "rental_days", "received", "refunded", "net",
               "bookings", "utilisation", "booked_value", "collected", "daily_rate", "amount", "paid", "balance",
               "outstanding_total", "verified_by"}
    aligns = ["L" if c in ("label", "customer", "vehicle", "reference", "verified_by", "status", "method", "channel")
              else "R" if c in numeric else "L" for c in report["columns"]]
    story += [p("Report details", "h2"), data_table(
        report["headers"], [[r.get(c, "") for c in report["columns"]] for r in report["rows"]],
        [width / n] * n, align=aligns,
    )]
    footer = " · ".join(x for x in (site.business_phone, site.business_email) if x)
    pdf = build_pdf(story, title=report["title"], author=site.business_name, landscape_mode=True,
                    footer=footer, footer_note=site_dict(site).get("website", ""))
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{report["slug"]}.pdf"'
    return resp


class ReportView(APIView):
    required_roles = FINANCE_ROLES

    def get(self, request, kind):
        if kind not in REPORTS:
            raise NotFound("Unknown report.")
        params = request.query_params
        year = int(params.get("year") or timezone.localdate().year)
        if not 2000 <= year <= 2100:
            raise ValidationError({"year": "Invalid year."})
        if kind == "bookings":
            report, slug = services.monthly_bookings(year), f"bookings-{year}"
            report["period_label"] = f"Reporting year: {year}"
        elif kind == "revenue":
            report, slug = services.monthly_revenue(year), f"revenue-{year}"
            report["period_label"] = f"Reporting year: {year}"
        elif kind == "vehicles":
            s, e = _range(params)
            report, slug = services.vehicle_performance(s, e), f"vehicles-{s}-{e}"
            report["period_label"] = f"Period: {s:%d %b %Y} to {e:%d %b %Y}"
        elif kind == "payments":
            s, e = _range(params)
            report, slug = services.payments_report(s, e), f"payments-{s}-{e}"
            report["period_label"] = f"Period: {s:%d %b %Y} to {e:%d %b %Y}"
        else:
            report, slug = services.outstanding_report(), f"outstanding-{date.today()}"
            report["period_label"] = f"As of {timezone.localdate():%d %b %Y}"
        report["slug"] = f"rafiki-{slug}"
        fmt = params.get("export")
        if fmt in ("csv", "pdf"):
            audit("report.exported", actor=request.user, request=request, summary=f"{kind} as {fmt}")
            return _to_csv(report) if fmt == "csv" else _to_pdf(report)
        return Response(report)
