from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from smart_extractor.schemas.common import LineItem


class _ReceiptBody(BaseModel):
    """Fields shared by Receipt and PartialReceipt."""

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 code, e.g. USD.")
    payment_method: str | None = None
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    tip: Decimal | None = Field(default=None, ge=0)
    total: Decimal = Field(ge=0)


class Receipt(_ReceiptBody):
    """Structured data extracted from a receipt.

    Merchant and date are None when the receipt does not show them, never guessed.
    """

    merchant_name: str | None = None
    purchased_at: datetime | None = None


class PartialReceipt(_ReceiptBody):
    """Label for a document whose merchant or date is unreadable (e.g. blurred in CORD).

    Metrics skip every field that is None here (not labeled): neither rewarded nor penalized.
    """

    merchant_name: str | None = None
    purchased_at: datetime | None = None
