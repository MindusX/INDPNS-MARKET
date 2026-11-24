from django.conf import settings


def get_provider():
    name = settings.PAYMENT_PROVIDER
    if name == "stripe":
        from .providers.stripe_provider import StripeProvider
        return StripeProvider()
    if name == "paypal":
        from .providers.paypal_provider import PayPalProvider
        return PayPalProvider()
    return None


def payments_enabled():
    p = get_provider()
    return bool(p and p.is_configured())
