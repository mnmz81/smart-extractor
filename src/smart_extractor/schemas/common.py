from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    """A single billed line on an invoice or receipt."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(description="Item or service description as printed.")
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    total: Decimal = Field(description="Line total, after quantity, before document-level tax.")
