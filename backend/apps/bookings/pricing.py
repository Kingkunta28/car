"""Authoritative pricing engine.

Every charge is computed here from database prices using Decimal. Totals
submitted by the browser are never read. The resulting ``Quote`` is
snapshotted onto the booking so later price changes never alter history.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.core.models import SiteSettings
from apps.core.utils import money

from .models import ExtraService, LocationType, PricingType

ZERO = Decimal("0.00")


@dataclass
class QuoteLine:
    code: str
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    kind: str  # rental | pickup | return | extra
    pricing_type: str = PricingType.PER_BOOKING
    extra_service_id: str | None = None

    def as_dict(self):
        return {
            "code": self.code, "description": self.description, "quantity": self.quantity,
            "unit_price": str(self.unit_price), "total": str(self.total), "kind": self.kind,
            "pricing_type": self.pricing_type,
        }


@dataclass
class Quote:
    rental_days: int
    daily_rate: Decimal
    lines: list[QuoteLine] = field(default_factory=list)
    tax_rate: Decimal = ZERO
    tax_label: str = ""
    currency: str = "USD"

    def _sum(self, *kinds):
        return money(sum((line.total for line in self.lines if line.kind in kinds), ZERO))

    @property
    def rental_total(self):
        return self._sum("rental")

    @property
    def pickup_fee(self):
        return self._sum("pickup")

    @property
    def return_fee(self):
        return self._sum("return")

    @property
    def extras_total(self):
        return self._sum("extra")

    @property
    def subtotal(self):
        return self._sum("rental", "pickup", "return", "extra")

    @property
    def tax_amount(self):
        return money(self.subtotal * self.tax_rate / Decimal("100"))

    @property
    def grand_total(self):
        return money(self.subtotal + self.tax_amount)

    def extra_lines(self):
        return [line for line in self.lines if line.kind == "extra"]

    def as_dict(self):
        return {
            "currency": self.currency,
            "rental_days": self.rental_days,
            "daily_rate": str(self.daily_rate),
            "lines": [line.as_dict() for line in self.lines],
            "rental_total": str(self.rental_total),
            "pickup_fee": str(self.pickup_fee),
            "return_fee": str(self.return_fee),
            "extras_total": str(self.extras_total),
            "subtotal": str(self.subtotal),
            "tax_rate": str(self.tax_rate),
            "tax_label": self.tax_label,
            "tax_amount": str(self.tax_amount),
            "grand_total": str(self.grand_total),
        }


def rental_days_between(pickup_at: datetime, return_at: datetime) -> int:
    """Each started 24-hour period is one rental day (minimum one)."""
    seconds = (return_at - pickup_at).total_seconds()
    if seconds <= 0:
        raise ValidationError({"return_date": "Return must be after pickup."})
    return max(1, math.ceil(seconds / 86400))


def _extra_total(extra: ExtraService, qty: int, days: int) -> tuple[Decimal, Decimal]:
    unit = money(extra.price)
    multiplier = {
        PricingType.PER_BOOKING: 1,
        PricingType.PER_UNIT: qty,
        PricingType.PER_DAY: days,
        PricingType.PER_UNIT_PER_DAY: qty * days,
    }[extra.pricing_type]
    return unit, money(unit * multiplier)


def build_quote(*, vehicle, pickup_at: datetime, return_at: datetime, pickup_type: str, return_type: str,
                extras: dict[str, int] | None = None, daily_rate: Decimal | None = None) -> Quote:
    """Calculate the full price.

    ``extras`` maps ExtraService.code -> requested quantity. Unknown,
    inactive or system location codes are rejected; quantities are bounded
    by ``max_quantity``. ``daily_rate`` overrides the vehicle's current
    rate (used when staff modify a booking, to keep the agreed price).
    """
    extras = {k: int(v) for k, v in (extras or {}).items() if int(v or 0) > 0}
    days = rental_days_between(pickup_at, return_at)
    site = SiteSettings.load()
    rate = money(daily_rate if daily_rate is not None else vehicle.price_per_day)
    quote = Quote(rental_days=days, daily_rate=rate, tax_rate=site.tax_rate, tax_label=site.tax_label)
    quote.lines.append(QuoteLine(
        code="rental", description=f"{vehicle.name} — {days} day{'s' if days != 1 else ''} × ${rate}",
        quantity=days, unit_price=rate, total=money(rate * days), kind="rental", pricing_type=PricingType.PER_DAY,
    ))

    services = {s.code: s for s in ExtraService.objects.filter(is_active=True)}
    zone = services.get(ExtraService.OUTSIDE_ZONE) or ExtraService.objects.filter(code=ExtraService.OUTSIDE_ZONE).first()
    for leg, loc in (("pickup", pickup_type), ("return", return_type)):
        if loc not in LocationType.values:
            raise ValidationError({f"{leg}_type": "Choose a valid location."})
        label = LocationType(loc).label
        fee = money(zone.price) if (loc == LocationType.OUTSIDE_ZONE and zone) else ZERO
        quote.lines.append(QuoteLine(
            code=f"{leg}_location", description=f"{leg.capitalize()}: {label}", quantity=1,
            unit_price=fee, total=fee, kind=leg,
        ))

    for code, qty in extras.items():
        svc = services.get(code)
        if svc is None or code == ExtraService.OUTSIDE_ZONE:
            raise ValidationError({"extras": f"'{code}' is not an available service."})
        if qty > svc.max_quantity:
            raise ValidationError({"extras": f"A maximum of {svc.max_quantity} × {svc.name} can be booked."})
        unit, total = _extra_total(svc, qty, days)
        quote.lines.append(QuoteLine(
            code=code, description=svc.name, quantity=qty, unit_price=unit, total=total, kind="extra",
            pricing_type=svc.pricing_type, extra_service_id=str(svc.pk),
        ))
    return quote
