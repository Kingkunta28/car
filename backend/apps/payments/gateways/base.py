"""Gateway abstraction. Add a provider by subclassing PaymentGateway and
registering it in ``registry.py``; nothing else in the codebase changes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


class GatewayError(Exception):
    """Raised when the provider is unreachable or rejects a request."""


@dataclass
class CheckoutSession:
    gateway_order_id: str
    redirect_url: str
    raw: dict = field(default_factory=dict)


@dataclass
class GatewayStatus:
    """Normalised, server-verified transaction status."""

    state: str  # "completed" | "failed" | "pending" | "reversed"
    amount: Decimal | None
    currency: str
    confirmation_code: str = ""
    merchant_reference: str = ""
    description: str = ""
    payment_method: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class RefundResult:
    accepted: bool
    reference: str = ""
    message: str = ""


class PaymentGateway(ABC):
    code: str = ""
    display_name: str = ""
    supported_currencies: tuple[str, ...] = ("USD",)
    supports_refunds: bool = False

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def create_checkout(self, *, payment, booking, callback_url: str, cancellation_url: str) -> CheckoutSession: ...

    @abstractmethod
    def fetch_status(self, gateway_order_id: str) -> GatewayStatus:
        """Ask the provider's API for the authoritative transaction state."""

    @abstractmethod
    def parse_webhook(self, request) -> str | None:
        """Return the gateway order id referenced by an incoming notification."""

    def webhook_ack(self, request, ok: bool):
        return {"status": 200 if ok else 500}

    def refund(self, *, payment, amount: Decimal, reason: str, requested_by: str) -> RefundResult:
        return RefundResult(accepted=False, message="Refunds are not supported by this gateway.")
