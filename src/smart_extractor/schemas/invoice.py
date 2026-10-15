from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from smart_extractor.schemas.common import LineItem


class Invoice(BaseModel):
    """Structured data extracted from an invoice."""

    model_config = ConfigDict(extra="forbid")

    invoice_number: str
    issue_date: date
    due_date: date | None = None
    vendor_name: str
    customer_name: str | None = None
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 code, e.g. USD.")
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    total: Decimal = Field(ge=0)
