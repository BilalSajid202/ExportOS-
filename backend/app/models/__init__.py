"""
ExportOS — Domain Models

Exports all SQLAlchemy declarative models and bases.
"""

from app.models.base import Base, BaseModel
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.inventory import (
    InventoryItem,
    InventoryTransaction,
    InventoryReservation,
    InventoryTransactionType,
    ReservationStatus,
    AvailabilityStatus,
)
from app.models.deal import Deal, DealLineItem, DealState
from app.models.artifact import Artifact, ArtifactType, InboundChannel
from app.models.extraction import ExtractionResult, ExtractionStatus

__all__ = [
    "Base",
    "BaseModel",
    "Organisation",
    "User",
    "UserRole",
    "Product",
    "InventoryItem",
    "InventoryTransaction",
    "InventoryReservation",
    "InventoryTransactionType",
    "ReservationStatus",
    "AvailabilityStatus",
    "Deal",
    "DealLineItem",
    "DealState",
    "Artifact",
    "ArtifactType",
    "InboundChannel",
    "ExtractionResult",
    "ExtractionStatus",
]
