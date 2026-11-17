from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class _Scoped(SimpleRateThrottle):
    """Named-scope throttle keyed by client IP regardless of authentication."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def scoped(name: str):
    return type(f"{name.title().replace('_', '')}Throttle", (_Scoped,), {"scope": name})


BookingCreateThrottle = scoped("booking_create")
QuoteThrottle = scoped("quote")
BookingAccessThrottle = scoped("booking_access")
PaymentThrottle = scoped("payment")
ContactThrottle = scoped("contact")
LoginThrottle = scoped("login")

__all__ = ["AnonRateThrottle", "BookingCreateThrottle", "QuoteThrottle", "BookingAccessThrottle",
           "PaymentThrottle", "ContactThrottle", "LoginThrottle"]
