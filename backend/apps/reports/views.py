import csv
import io
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from reportlab.lib.units import mm
from reportlab.platypus import Spacer, Table, TableStyle

from apps.accounts.permissions import ALL_ROLES, FINANCE_ROLES
from apps.core.models import SiteSettings
from apps.core.pdf import BORDER, LIGHT, build_pdf, esc, p
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
    width = 267 * mm
    data = [[p(f"<b>{esc(h)}</b>", "label") for h in report["headers"]]]
    data += [[p(esc(r.get(c, "")), "small") for c in report["columns"]] for r in report["rows"]]
    t = Table(data, colWidths=[width / n] * n, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story = [p(f"{esc(site.business_name)} — {esc(report['title'])}", "h1"), Spacer(1, 2 * mm),
             p(f"Generated {timezone.localtime():%d %b %Y %H:%M} (EAT)", "small"), Spacer(1, 5 * mm), t]
    for k, v in (report.get("summary") or {}).items():
        story += [Spacer(1, 3 * mm), p(f"<b>{esc(k.replace('_', ' ').title())}:</b> {esc(v)}")]
    pdf = build_pdf(story, title=report["title"], author=site.business_name, landscape_mode=True)
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
        elif kind == "revenue":
            report, slug = services.monthly_revenue(year), f"revenue-{year}"
        elif kind == "vehicles":
            s, e = _range(params)
            report, slug = services.vehicle_performance(s, e), f"vehicles-{s}-{e}"
        elif kind == "payments":
            s, e = _range(params)
            report, slug = services.payments_report(s, e), f"payments-{s}-{e}"
        else:
            report, slug = services.outstanding_report(), f"outstanding-{date.today()}"
        report["slug"] = f"rafiki-{slug}"
        fmt = params.get("export")
        if fmt in ("csv", "pdf"):
            audit("report.exported", actor=request.user, request=request, summary=f"{kind} as {fmt}")
            return _to_csv(report) if fmt == "csv" else _to_pdf(report)
        return Response(report)
