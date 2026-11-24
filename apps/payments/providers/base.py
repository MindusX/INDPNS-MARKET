from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class PaymentError(Exception):
    pass


class SignatureError(PaymentError):
    pass


@dataclass
class CheckoutResult:
    url: str
    provider_ref: str


@dataclass
class WebhookResult:
    event_id: str
    event_type: str
    order_number: str = ""
    paid: bool = False
    amount_cents: int | None = None
    provider_ref: str = ""
    payment_ref: str = ""
    raw: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    """Couche abstraite : le reste du code ne dépend jamais d'un prestataire précis."""
    name = ""

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def create_checkout(self, order, success_url: str, cancel_url: str) -> CheckoutResult: ...

    @abstractmethod
    def parse_webhook(self, payload: bytes, headers) -> WebhookResult: ...

    @abstractmethod
    def refund(self, order) -> None: ...
