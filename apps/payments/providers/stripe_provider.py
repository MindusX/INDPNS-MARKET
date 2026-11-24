from decimal import Decimal

from django.conf import settings

from .base import CheckoutResult, PaymentError, PaymentProvider, SignatureError, WebhookResult


def to_cents(amount):
    return int((Decimal(amount) * 100).to_integral_value())


class StripeProvider(PaymentProvider):
    name = "stripe"

    def is_configured(self):
        return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)

    def _api(self):
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        return stripe

    def create_checkout(self, order, success_url, cancel_url):
        stripe = self._api()
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                client_reference_id=order.number,
                customer_email=order.buyer.email,
                line_items=[{"quantity": 1, "price_data": {
                    "currency": order.currency.lower(), "unit_amount": to_cents(i.unit_price),
                    "product_data": {"name": i.title_snapshot[:120]}}} for i in order.items.all()],
                metadata={"order_number": order.number},
                payment_intent_data={"metadata": {"order_number": order.number}},
                success_url=success_url, cancel_url=cancel_url,
                idempotency_key=f"checkout-{order.idempotency_key}",
            )
        except Exception as exc:
            raise PaymentError("The payment provider could not start the checkout. Please try again.") from exc
        return CheckoutResult(url=session.url, provider_ref=session.id)

    def parse_webhook(self, payload, headers):
        stripe = self._api()
        try:
            event = stripe.Webhook.construct_event(payload, headers.get("Stripe-Signature", ""), settings.STRIPE_WEBHOOK_SECRET)
        except Exception as exc:   # signature invalide ou payload illisible
            raise SignatureError(str(exc)) from exc
        obj = event["data"]["object"]
        res = WebhookResult(event_id=event["id"], event_type=event["type"], raw={"type": event["type"]})
        if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            res.order_number = (obj.get("metadata") or {}).get("order_number") or obj.get("client_reference_id") or ""
            res.paid = obj.get("payment_status") == "paid"
            res.amount_cents = obj.get("amount_total")
            res.provider_ref = obj.get("id", "")
            res.payment_ref = obj.get("payment_intent") or ""
        return res

    def refund(self, order):
        from .base import PaymentError
        from apps.payments.models import PaymentTransaction
        tx = PaymentTransaction.objects.filter(order=order, status="succeeded").exclude(payment_ref="").first()
        if tx is None:
            raise PaymentError("No payment reference found for this order.")
        stripe = self._api()
        try:
            stripe.Refund.create(payment_intent=tx.payment_ref, idempotency_key=f"refund-{order.idempotency_key}")
        except Exception as exc:
            raise PaymentError("The provider refused the refund.") from exc
        tx.status = "refunded"
        tx.save(update_fields=["status", "updated_at"])
