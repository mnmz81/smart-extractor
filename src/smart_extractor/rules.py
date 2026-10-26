"""Business-rule checks on an extracted document, as messages a model can act on.

Kept out of the schemas on purpose: the same schemas validate the labels, and real labels
can carry rounding quirks that must still load.
"""

from datetime import date, datetime
from decimal import Decimal

from smart_extractor.metrics import Document
from smart_extractor.schemas import Invoice, LineItem, PartialReceipt, Receipt

_TOLERANCE = Decimal("0.01")  # one cent of rounding


def _close(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= _TOLERANCE


def _line_errors(item: LineItem) -> list[str]:
    if item.unit_price is not None and not _close(item.quantity * item.unit_price, item.total):
        return [
            f"line item '{item.description}': quantity {item.quantity} x unit_price "
            f"{item.unit_price} is {item.quantity * item.unit_price}, but total is {item.total}"
        ]
    return []


def check_document(doc: Document, today: date | None = None) -> list[str]:
    """Return one message per broken rule; an empty list means the document passes."""
    today = today or date.today()
    errors = [e for item in doc.line_items for e in _line_errors(item)]
    items_sum = sum((i.total for i in doc.line_items), Decimal("0"))
    if doc.subtotal is not None and not _close(items_sum, doc.subtotal):
        errors.append(f"line item totals add up to {items_sum}, but subtotal is {doc.subtotal}")
    if doc.subtotal is not None and doc.tax is not None:
        tip = getattr(doc, "tip", None) or Decimal("0")
        added = doc.subtotal + doc.tax + tip
        included = doc.subtotal + tip  # tax-inclusive pricing: the tax is already inside subtotal
        if not (_close(added, doc.total) or _close(included, doc.total)):
            errors.append(
                f"subtotal + tax + tip is {added} (or {included} if tax is included in the "
                f"subtotal), but total is {doc.total}"
            )
    if not (doc.currency.isalpha() and doc.currency.isupper()):
        errors.append(f"currency '{doc.currency}' is not an uppercase ISO 4217 code")
    if isinstance(doc, Invoice):
        if doc.due_date is not None and doc.due_date < doc.issue_date:
            errors.append(f"due_date {doc.due_date} is before issue_date {doc.issue_date}")
        if doc.issue_date > today:
            errors.append(f"issue_date {doc.issue_date} is in the future")
    elif isinstance(doc, Receipt | PartialReceipt):
        purchased = doc.purchased_at
        if isinstance(purchased, datetime) and purchased.date() > today:
            errors.append(f"purchased_at {purchased} is in the future")
    return errors
