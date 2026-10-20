"""Generate fake but schema-valid documents. The generated model is the label."""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from faker import Faker

from smart_extractor.schemas import Invoice, LineItem, Receipt

Lang = Literal["he", "en"]
_LOCALES: dict[Lang, str] = {"en": "en_US", "he": "he_IL"}
_CURRENCY: dict[Lang, str] = {"en": "USD", "he": "ILS"}
_TAX_RATE = {"en": Decimal("0.08"), "he": Decimal("0.18")}
_CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _make_items(fake: Faker, lang: Lang) -> list[LineItem]:
    items: list[LineItem] = []
    for _ in range(fake.random_int(min=1, max=6)):
        quantity = Decimal(fake.random_int(min=1, max=10))
        unit_price = _money(Decimal(fake.random_int(min=100, max=50000)) / 100)
        items.append(
            LineItem(
                description=fake.catch_phrase() if lang == "en" else fake.word(),
                quantity=quantity,
                unit_price=unit_price,
                total=_money(quantity * unit_price),
            )
        )
    return items


def _faker(seed: int, lang: Lang) -> Faker:
    fake = Faker(_LOCALES[lang])
    fake.seed_instance(seed)
    return fake


def make_invoice(seed: int, lang: Lang = "en") -> Invoice:
    """Same seed and lang always give the same invoice."""
    fake = _faker(seed, lang)
    items = _make_items(fake, lang)
    subtotal = sum((i.total for i in items), Decimal("0"))
    tax = _money(subtotal * _TAX_RATE[lang])
    issue_date = fake.date_between(start_date="-1y", end_date="today")

    return Invoice(
        invoice_number=f"INV-{fake.random_int(min=1000, max=99999)}",
        issue_date=issue_date,
        due_date=issue_date + timedelta(days=30),
        vendor_name=fake.company(),
        customer_name=fake.name(),
        currency=_CURRENCY[lang],
        line_items=items,
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
    )


def make_receipt(seed: int, lang: Lang = "en") -> Receipt:
    """Same seed and lang always give the same receipt."""
    fake = _faker(seed, lang)
    items = _make_items(fake, lang)
    subtotal = sum((i.total for i in items), Decimal("0"))
    tax = _money(subtotal * _TAX_RATE[lang])
    tip = _money(subtotal * Decimal("0.10")) if fake.boolean() else None

    return Receipt(
        merchant_name=fake.company(),
        purchased_at=fake.date_time_between(start_date="-1y", end_date="now"),
        currency=_CURRENCY[lang],
        payment_method=fake.random_element(["cash", "card"]),
        line_items=items,
        subtotal=subtotal,
        tax=tax,
        tip=tip,
        total=subtotal + tax + (tip or Decimal("0")),
    )
