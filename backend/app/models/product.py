"""
ExportOS — Product Catalogue Model

Represents a sellable catalogue item (SKU) belonging to an Organisation.
Inventory items reference products via product_id.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.inventory import InventoryItem


class Product(BaseModel):
    """
    Product catalogue entity with packing and classification defaults.
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "organisation_id",
            "sku",
            name="uq_products_organisation_id_sku",
        ),
    )

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(20), default="PCS", nullable=False)
    selling_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    default_hs_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    carton_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    base_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)

    organisation: Mapped["Organisation"] = relationship("Organisation", lazy="joined")
    inventory_item: Mapped[Optional["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku='{self.sku}' name='{self.name}'>"
