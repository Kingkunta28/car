from django.conf import settings

from .base import PaymentGateway
from .pesapal import PesapalGateway

GATEWAYS: dict[str, type[PaymentGateway]] = {
    PesapalGateway.code: PesapalGateway,
    # Register additional providers here, e.g. "flutterwave": FlutterwaveGateway
}


def get_gateway(code: str) -> PaymentGateway | None:
    if code not in settings.PAYMENT_GATEWAYS_ENABLED:
        return None
    cls = GATEWAYS.get(code)
    return cls() if cls else None


def available_gateways() -> list[PaymentGateway]:
    """Enabled AND fully configured gateways, in configured order."""
    out = []
    for code in settings.PAYMENT_GATEWAYS_ENABLED:
        gw = get_gateway(code)
        if gw and gw.is_configured():
            out.append(gw)
    return out
