from .base import PaymentError, PaymentProvider


class PayPalProvider(PaymentProvider):
    """Adaptateur PayPal : NON IMPLÉMENTÉ. is_configured() reste False afin de ne jamais présenter PayPal comme actif."""
    name = "paypal"

    def is_configured(self):
        return False

    def create_checkout(self, order, success_url, cancel_url):
        raise PaymentError("PayPal adapter is not implemented.")

    def parse_webhook(self, payload, headers):
        raise PaymentError("PayPal adapter is not implemented.")

    def refund(self, order):
        raise PaymentError("PayPal adapter is not implemented.")
