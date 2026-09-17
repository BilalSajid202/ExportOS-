"""
ExportOS — Product Catalogue Pydantic Schemas
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCreateRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100, description="Unique SKU within organisation")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    unit_of_measure: str = Field(default="PCS", max_length=20)
    selling_currency: str = Field(default="USD", min_length=3, max_length=3)
    default_hs_code: Optional[str] = Field(None, max_length=20)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    carton_capacity: Optional[int] = Field(None, ge=1)
    base_cost: Optional[Decimal] = Field(None, ge=0)


class ProductUpdateRequest(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    selling_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    default_hs_code: Optional[str] = Field(None, max_length=20)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    carton_capacity: Optional[int] = Field(None, ge=1)
    base_cost: Optional[Decimal] = Field(None, ge=0)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    sku: str
    name: str
    description: Optional[str] = None
    unit_of_measure: str
    selling_currency: str
    default_hs_code: Optional[str] = None
    weight_kg: Optional[Decimal] = None
    carton_capacity: Optional[int] = None
    base_cost: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
