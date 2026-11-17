"""Pesapal API 3.0 (https://developer.pesapal.com).

Flow: RequestToken → SubmitOrderRequest (redirect guest) → Pesapal calls our
IPN URL and redirects the guest back → we call GetTransactionStatus and only
that server-to-server response can mark a payment as completed.
"""
import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache

from .base import CheckoutSession, GatewayError, GatewayStatus, PaymentGateway, RefundResult

logger = logging.getLogger(__name__)

BASE_URLS = {
    "sandbox": "https://cybqa.pesapal.com/pesapalv3",
    "live": "https://pay.pesapal.com/v3",
}
STATUS_MAP = {0: "pending", 1: "completed", 2: "failed", 3: "reversed"}


class PesapalGateway(PaymentGateway):
    code = "pesapal"
    display_name = "Pesapal (Visa, Mastercard, mobile money)"
    supported_currencies = ("USD", "TZS", "KES", "UGX")
    supports_refunds = True
    timeout = 20

    @property
    def base_url(self):
        return BASE_URLS["live" if settings.PESAPAL_ENV == "live" else "sandbox"]

    def is_configured(self) -> bool:
        return bool(settings.PESAPAL_CONSUMER_KEY and settings.PESAPAL_CONSUMER_SECRET and settings.PESAPAL_IPN_ID)

    # -- HTTP helpers -------------------------------------------------------
    def _headers(self, token=None):
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _request(self, method, path, *, token=True, **kwargs):
        headers = self._headers(self._token() if token else None)
        try:
            resp = requests.request(method, f"{self.base_url}{path}", headers=headers, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise GatewayError(f"Pesapal is unreachable: {exc.__class__.__name__}") from exc
        try:
            data = resp.json()
        except ValueError as exc:
            raise GatewayError(f"Pesapal returned an invalid response (HTTP {resp.status_code}).") from exc
        err = data.get("error") if isinstance(data, dict) else None
        if resp.status_code >= 400 or (err and (err.get("code") or err.get("message"))):
            msg = (err or {}).get("message") or f"HTTP {resp.status_code}"
            raise GatewayError(f"Pesapal error: {msg}")
        return data

    def _token(self) -> str:
        key = f"pesapal-token-{settings.PESAPAL_ENV}"
        token = cache.get(key)
        if token:
            return token
        data = self._request("POST", "/api/Auth/RequestToken", token=False, json={
            "consumer_key": settings.PESAPAL_CONSUMER_KEY, "consumer_secret": settings.PESAPAL_CONSUMER_SECRET,
        })
        token = data.get("token")
        if not token:
            raise GatewayError("Pesapal did not return an access token.")
        cache.set(key, token, 240)  # tokens are valid for 5 minutes
        return token

    # -- API ------------------------------------------------------------------
    def register_ipn(self, url: str) -> dict:
        return self._request("POST", "/api/URLSetup/RegisterIPN", json={"url": url, "ipn_notification_type": "GET"})

    def create_checkout(self, *, payment, booking, callback_url, cancellation_url) -> CheckoutSession:
        if not self.is_configured():
            raise GatewayError("Online payments are not configured yet.")
        names = booking.customer.full_name.split()
        body = {
            "id": payment.payment_reference,
            "currency": payment.currency,
            "amount": float(payment.amount),
            "description": f"Rafiki Car Hire booking {booking.booking_reference}"[:100],
            "callback_url": callback_url,
            "cancellation_url": cancellation_url,
            "notification_id": settings.PESAPAL_IPN_ID,
            "billing_address": {
                "email_address": booking.customer.email,
                "phone_number": booking.customer.phone,
                "first_name": names[0] if names else "",
                "last_name": " ".join(names[1:]) if len(names) > 1 else "",
            },
        }
        data = self._request("POST", "/api/Transactions/SubmitOrderRequest", json=body)
        if not data.get("order_tracking_id") or not data.get("redirect_url"):
            raise GatewayError("Pesapal did not return a checkout URL.")
        return CheckoutSession(gateway_order_id=data["order_tracking_id"], redirect_url=data["redirect_url"],
                               raw={k: data.get(k) for k in ("order_tracking_id", "merchant_reference", "status")})

    def fetch_status(self, gateway_order_id: str) -> GatewayStatus:
        data = self._request("GET", "/api/Transactions/GetTransactionStatus",
                             params={"orderTrackingId": gateway_order_id})
        try:
            amount = Decimal(str(data.get("amount"))) if data.get("amount") is not None else None
        except InvalidOperation:
            amount = None
        code = data.get("status_code")
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = 0
        safe = {k: data.get(k) for k in ("payment_method", "amount", "created_date", "confirmation_code",
                                          "payment_status_description", "status_code", "merchant_reference",
                                          "currency", "payment_account")}
        return GatewayStatus(
            state=STATUS_MAP.get(code, "pending"), amount=amount, currency=(data.get("currency") or "").upper(),
            confirmation_code=data.get("confirmation_code") or "", merchant_reference=data.get("merchant_reference") or "",
            description=data.get("payment_status_description") or "", payment_method=data.get("payment_method") or "",
            raw=safe,
        )

    def parse_webhook(self, request):
        src = request.query_params if request.method == "GET" else (request.data or request.query_params)
        return src.get("OrderTrackingId") or src.get("orderTrackingId")

    def webhook_ack(self, request, ok: bool):
        src = request.query_params if request.method == "GET" else (request.data or request.query_params)
        return {
            "orderNotificationType": src.get("OrderNotificationType", "IPNCHANGE"),
            "orderTrackingId": src.get("OrderTrackingId", ""),
            "orderMerchantReference": src.get("OrderMerchantReference", ""),
            "status": 200 if ok else 500,
        }

    def refund(self, *, payment, amount, reason, requested_by) -> RefundResult:
        if not payment.transaction_reference:
            return RefundResult(accepted=False, message="No Pesapal confirmation code on this payment.")
        data = self._request("POST", "/api/Transactions/RefundRequest", json={
            "confirmation_code": payment.transaction_reference, "amount": str(amount),
            "username": requested_by[:50], "remarks": reason[:100],
        })
        ok = str(data.get("status")) == "200"
        return RefundResult(accepted=ok, message=data.get("message", ""))
