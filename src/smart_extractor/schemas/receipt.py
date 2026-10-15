from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from smart_extractor.schemas.common import LineItem


class Receipt(BaseModel):
    """Structured data extracted from a receipt."""

    model_config = ConfigDict(extra="forbid")

    merchant_name: str
    purchased_at: datetime
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 code, e.g. USD.")
    payment_method: str | None = None
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    tip: Decimal | None = Field(default=None, ge=0)
    total: Decimal = Field(ge=0)
