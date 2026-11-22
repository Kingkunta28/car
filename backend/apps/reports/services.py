"""Reporting queries. Money figures are Decimal and based on VERIFIED payments only."""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
from apps.core.utils import money
from apps.payments.models import Payment, Refund, Status
from apps.vehicles.models import AvailabilityStatus, Vehicle

ACTIVE = [BookingStatus.PENDING_CONFIRMATION, BookingStatus.CONFIRMED, BookingStatus.COMPLETED]
ZERO = Decimal("0.00")


def _d(v):
    return money(v or 0)


def dashboard() -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    b = Booking.objects
    counts = b.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(booking_status=BookingStatus.PENDING_CONFIRMATION)),
        confirmed=Count("id", filter=Q(booking_status=BookingStatus.CONFIRMED)),
        completed=Count("id", filter=Q(booking_status=BookingStatus.COMPLETED)),
        cancelled=Count("id", filter=Q(booking_status__in=[BookingStatus.CANCELLED, BookingStatus.REJECTED,
                                                            BookingStatus.EXPIRED])),
    )
    paid = Payment.objects.filter(payment_status=Status.VERIFIED).aggregate(
        gross=Sum("amount"), refunded=Sum("refunded_amount"))
    month_paid = Payment.objects.filter(payment_status=Status.VERIFIED, verified_at__date__gte=month_start).aggregate(
        gross=Sum("amount"), refunded=Sum("refunded_amount"))
    outstanding = b.filter(booking_status__in=ACTIVE, amount_paid__lt=F("grand_total")).aggregate(
        due=Sum(F("grand_total") - F("amount_paid")), n=Count("id"))
    vehicles = Vehicle.objects.filter(is_active=True)
    now = timezone.now()
    on_rent = set(b.filter(booking_status=BookingStatus.CONFIRMED, pickup_at__lte=now, return_at__gte=now)
                  .values_list("vehicle_slug", flat=True))
    upcoming = list(b.filter(booking_status=BookingStatus.CONFIRMED, pickup_date__gte=today,
                             pickup_date__lte=today + timedelta(days=7)).select_related("customer")
                    .order_by("pickup_at")[:10])
    awaiting = list(b.filter(booking_status=BookingStatus.PENDING_CONFIRMATION).select_related("customer")
                    .order_by("hold_expires_at")[:10])
    return {
        "bookings": counts,
        "revenue": {"total": str(_d(paid["gross"]) - _d(paid["refunded"])),
                    "this_month": str(_d(month_paid["gross"]) - _d(month_paid["refunded"]))},
        "outstanding": {"amount": str(_d(outstanding["due"])), "bookings": outstanding["n"]},
        "vehicles": {
            "total": vehicles.count(),
            "available": vehicles.filter(availability_status=AvailabilityStatus.AVAILABLE).exclude(slug__in=on_rent).count(),
            "on_rent": len(set(on_rent)),
            "maintenance": vehicles.filter(availability_status=AvailabilityStatus.MAINTENANCE).count(),
        },
        "pending_payments": Payment.objects.filter(payment_status=Status.PENDING_VERIFICATION).count(),
        "upcoming_pickups": [{"id": x.pk, "booking_reference": x.booking_reference, "pickup_date": x.pickup_date,
                              "pickup_time": x.pickup_time, "pickup_type": x.pickup_type,
                              "customer__full_name": x.customer.full_name, "vehicle__name": x.vehicle_name}
                             for x in upcoming],
        "awaiting_confirmation": [{"id": x.pk, "booking_reference": x.booking_reference,
                                   "customer__full_name": x.customer.full_name, "vehicle__name": x.vehicle_name,
                                   "pickup_date": x.pickup_date, "grand_total": x.grand_total,
                                   "hold_expires_at": x.hold_expires_at} for x in awaiting],
    }


def _month_rows(year):
    return {m: {"month": m, "label": calendar.month_name[m]} for m in range(1, 13)}


def monthly_bookings(year: int) -> dict:
    rows = _month_rows(year)
    qs = (Booking.objects.filter(created_at__year=year).annotate(m=ExtractMonth("created_at")).values("m")
          .annotate(total=Count("id"),
                    confirmed=Count("id", filter=Q(booking_status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED])),
                    pending=Count("id", filter=Q(booking_status=BookingStatus.PENDING_CONFIRMATION)),
                    lost=Count("id", filter=Q(booking_status__in=[BookingStatus.CANCELLED, BookingStatus.REJECTED,
                                                                   BookingStatus.EXPIRED])),
                    days=Sum("rental_days", filter=Q(booking_status__in=ACTIVE)),
                    value=Sum("grand_total", filter=Q(booking_status__in=ACTIVE))))
    for r in qs:
        rows[r["m"]].update(total=r["total"], confirmed=r["confirmed"], pending=r["pending"], lost=r["lost"],
                            rental_days=r["days"] or 0, booked_value=str(_d(r["value"])))
    out = []
    for m in range(1, 13):
        row = {"total": 0, "confirmed": 0, "pending": 0, "lost": 0, "rental_days": 0, "booked_value": "0.00",
               **rows[m]}
        out.append(row)
    return {"title": f"Monthly bookings {year}",
            "columns": ["label", "total", "confirmed", "pending", "lost", "rental_days", "booked_value"],
            "headers": ["Month", "Requests", "Confirmed/completed", "Pending", "Cancelled/rejected/expired",
                        "Rental days", "Booked value (USD)"],
            "rows": out}


def monthly_revenue(year: int) -> dict:
    received = {r["m"]: _d(r["s"]) for r in Payment.objects.filter(payment_status=Status.VERIFIED,
                                                                     verified_at__year=year)
                .annotate(m=ExtractMonth("verified_at")).values("m").annotate(s=Sum("amount"))}
    refunded = {r["m"]: _d(r["s"]) for r in Refund.objects.filter(created_at__year=year).exclude(status="FAILED")
                .annotate(m=ExtractMonth("created_at")).values("m").annotate(s=Sum("amount"))}
    rows, total = [], ZERO
    for m in range(1, 13):
        g, rf = received.get(m, ZERO), refunded.get(m, ZERO)
        total += g - rf
        rows.append({"label": calendar.month_name[m], "received": str(g), "refunded": str(rf), "net": str(g - rf)})
    year_bookings = Booking.objects.filter(created_at__year=year)
    counts = year_bookings.aggregate(
        total=Count("id"),
        confirmed=Count("id", filter=Q(booking_status=BookingStatus.CONFIRMED)),
        completed=Count("id", filter=Q(booking_status=BookingStatus.COMPLETED)),
    )
    outstanding = Booking.objects.filter(booking_status__in=ACTIVE, amount_paid__lt=F("grand_total")) \
        .aggregate(amount=Sum(F("grand_total") - F("amount_paid")))
    vehicle_rows = []
    for vehicle in Vehicle.objects.all():
        metrics = vehicle.bookings.filter(
            booking_status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED],
            pickup_date__year=year,
        ).aggregate(bookings=Count("id"), days=Sum("rental_days"), value=Sum("grand_total"))
        vehicle_rows.append((metrics["value"] or ZERO, vehicle.name, metrics["bookings"], metrics["days"] or 0))
    static_metrics = {}
    for booking in Booking.objects.filter(vehicle__isnull=True, booking_status__in=[BookingStatus.CONFIRMED,
                                                                                   BookingStatus.COMPLETED],
                                          pickup_date__year=year).only("vehicle_slug", "vehicle_snapshot", "rental_days",
                                                                         "grand_total"):
        item = static_metrics.setdefault(booking.vehicle_slug, {"name": booking.vehicle_name, "count": 0,
                                                                 "days": 0, "value": ZERO})
        item["count"] += 1
        item["days"] += booking.rental_days
        item["value"] += booking.grand_total
    vehicle_rows.extend((item["value"], item["name"], item["count"], item["days"])
                        for item in static_metrics.values())
    vehicle_rows.sort(reverse=True)
    top_vehicles = "; ".join(f"{name} ({count} bookings, {days} rental days)"
                              for _, name, count, days in vehicle_rows[:5] if count)
    return {"title": f"Monthly revenue {year} (verified payments)", "columns": ["label", "received", "refunded", "net"],
            "headers": ["Month", "Received (USD)", "Refunded (USD)", "Net (USD)"], "rows": rows,
            "summary": {"total_bookings": counts["total"], "confirmed_bookings": counts["confirmed"],
                        "completed_bookings": counts["completed"],
                        "payments_received_usd": str(sum(received.values(), ZERO)),
                        "refunds_usd": str(sum(refunded.values(), ZERO)), "net_total_usd": str(total),
                        "outstanding_balances_usd": str(_d(outstanding["amount"])),
                        "vehicle_performance_top_5": top_vehicles or "No confirmed or completed rentals"}}


def vehicle_performance(start: date, end: date) -> dict:
    period_days = max((end - start).days + 1, 1)
    rows = []
    for v in Vehicle.objects.all().order_by("name"):
        qs = v.bookings.filter(booking_status__in=[BookingStatus.CONFIRMED, BookingStatus.COMPLETED],
                               pickup_date__gte=start, pickup_date__lte=end)
        agg = qs.aggregate(n=Count("id"), days=Sum("rental_days"), value=Sum("grand_total"), paid=Sum("amount_paid"))
        days = agg["days"] or 0
        rows.append({"label": v.name, "bookings": agg["n"], "rental_days": days,
                     "utilisation": f"{min(100, round(days * 100 / period_days))}%",
                     "booked_value": str(_d(agg["value"])), "collected": str(_d(agg["paid"])),
                     "daily_rate": str(v.price_per_day), "active": "Yes" if v.is_active else "No"})
    static_metrics = {}
    for booking in Booking.objects.filter(vehicle__isnull=True, booking_status__in=[BookingStatus.CONFIRMED,
                                                                                   BookingStatus.COMPLETED],
                                          pickup_date__gte=start, pickup_date__lte=end).only(
                                              "vehicle_slug", "vehicle_snapshot", "rental_days", "grand_total", "amount_paid"):
        item = static_metrics.setdefault(booking.vehicle_slug, {
            "label": booking.vehicle_name, "bookings": 0, "rental_days": 0, "booked_value": ZERO,
            "collected": ZERO, "daily_rate": booking.vehicle_snapshot.get("price_per_day", booking.daily_rate),
            "active": "Yes" if booking.vehicle_snapshot.get("availability_status", "AVAILABLE") == "AVAILABLE" else "No",
        })
        item["bookings"] += 1
        item["rental_days"] += booking.rental_days
        item["booked_value"] += booking.grand_total
        item["collected"] += booking.amount_paid
    for item in static_metrics.values():
        item["utilisation"] = f"{min(100, round(item['rental_days'] * 100 / period_days))}%"
        item["booked_value"] = str(_d(item["booked_value"]))
        item["collected"] = str(_d(item["collected"]))
        item["daily_rate"] = str(item["daily_rate"])
        rows.append(item)
    rows.sort(key=lambda r: Decimal(r["booked_value"]), reverse=True)
    return {"title": f"Vehicle performance {start:%d %b %Y} – {end:%d %b %Y}",
            "columns": ["label", "bookings", "rental_days", "utilisation", "booked_value", "collected", "daily_rate",
                        "active"],
            "headers": ["Vehicle", "Bookings", "Rental days", "Utilisation", "Booked value", "Collected",
                        "Current rate", "Active"],
            "rows": rows}


def payments_report(start: date, end: date) -> dict:
    qs = Payment.objects.filter(created_at__date__gte=start, created_at__date__lte=end) \
        .select_related("booking", "booking__customer", "verified_by").order_by("created_at")
    rows = [{"label": p.payment_reference, "date": f"{timezone.localtime(p.created_at):%Y-%m-%d}",
             "booking": p.booking.booking_reference, "customer": p.booking.customer.full_name,
             "method": p.get_payment_method_display(), "channel": p.get_channel_display() if p.channel else "",
             "status": p.get_payment_status_display(), "amount": str(p.amount), "refunded": str(p.refunded_amount),
             "reference": p.transaction_reference, "verified_by": p.verified_by.full_name if p.verified_by else
             (p.get_verification_source_display() if p.verification_source else "")} for p in qs]
    verified = sum((Decimal(r["amount"]) - Decimal(r["refunded"]) for r, p in zip(rows, qs)
                    if p.payment_status == Status.VERIFIED), ZERO)
    return {"title": f"Payments {start:%d %b %Y} – {end:%d %b %Y}",
            "columns": ["label", "date", "booking", "customer", "method", "channel", "status", "amount", "refunded",
                        "reference", "verified_by"],
            "headers": ["Payment", "Date", "Booking", "Customer", "Method", "Channel", "Status", "Amount", "Refunded",
                        "Txn ref.", "Verified by"],
            "rows": rows, "summary": {"verified_net": str(money(verified))}}


def outstanding_report() -> dict:
    qs = Booking.objects.filter(booking_status__in=ACTIVE, amount_paid__lt=F("grand_total")) \
        .select_related("customer", "vehicle").order_by("pickup_date")
    rows = [{"label": b.booking_reference, "customer": b.customer.full_name, "phone": b.customer.phone,
             "vehicle": b.vehicle_name, "pickup": f"{b.pickup_date:%Y-%m-%d}", "status": b.get_booking_status_display(),
             "total": str(b.grand_total), "paid": str(b.amount_paid), "balance": str(b.balance_due)} for b in qs]
    total = sum((Decimal(r["balance"]) for r in rows), ZERO)
    return {"title": f"Outstanding balances at {timezone.localdate():%d %b %Y}",
            "columns": ["label", "customer", "phone", "vehicle", "pickup", "status", "total", "paid", "balance"],
            "headers": ["Booking", "Customer", "Phone", "Vehicle", "Pickup", "Status", "Total", "Paid", "Balance"],
            "rows": rows, "summary": {"outstanding_total": str(money(total))}}
