import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Numeric,
    Integer,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class TransportMode(str, enum.Enum):
    OCEAN_FCL = "OCEAN_FCL"
    OCEAN_LCL = "OCEAN_LCL"
    AIR_FREIGHT = "AIR_FREIGHT"
    LAND_TRUCK = "LAND_TRUCK"


class ShipmentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    BOOKED = "BOOKED"
    CARGO_READY = "CARGO_READY"
    STUFFED = "STUFFED"
    GATED_IN = "GATED_IN"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED_PORT = "ARRIVED_PORT"
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class FreightTerms(str, enum.Enum):
    FREIGHT_PREPAID = "FREIGHT_PREPAID"
    FREIGHT_COLLECT = "FREIGHT_COLLECT"


class MilestoneType(str, enum.Enum):
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    CARGO_READY = "CARGO_READY"
    CONTAINER_STUFFING = "CONTAINER_STUFFING"
    PORT_GATE_IN = "PORT_GATE_IN"
    CUSTOMS_OUT_CHARGE_WEBOC = "CUSTOMS_OUT_CHARGE_WEBOC"
    VESSEL_DEPARTURE = "VESSEL_DEPARTURE"
    IN_TRANSIT_TRANSSHIPMENT = "IN_TRANSIT_TRANSSHIPMENT"
    DESTINATION_ARRIVAL = "DESTINATION_ARRIVAL"
    CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE"
    FINAL_DELIVERY = "FINAL_DELIVERY"


class MilestoneStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    SKIPPED = "SKIPPED"


class PaymentType(str, enum.Enum):
    ADVANCE = "ADVANCE"
    LC_DRAWING = "LC_DRAWING"
    DP_COLLECTION = "DP_COLLECTION"
    DA_COLLECTION = "DA_COLLECTION"
    OPEN_ACCOUNT = "OPEN_ACCOUNT"
    BANK_TRANSFER = "BANK_TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    FULLY_PAID = "FULLY_PAID"
    OVERPAID = "OVERPAID"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tracking_number = Column(String(100), unique=True, nullable=False, index=True)
    transport_mode = Column(
        SQLEnum(TransportMode, name="transportmode"),
        nullable=False,
        default=TransportMode.OCEAN_FCL,
    )
    status = Column(
        SQLEnum(ShipmentStatus, name="shipmentstatus"),
        nullable=False,
        default=ShipmentStatus.DRAFT,
        index=True,
    )
    freight_terms = Column(
        SQLEnum(FreightTerms, name="freightterms"),
        nullable=False,
        default=FreightTerms.FREIGHT_PREPAID,
    )

    # Carrier & Booking Reference
    carrier_name = Column(String(255), nullable=True)
    vessel_or_flight = Column(String(255), nullable=True)
    voyage_number = Column(String(100), nullable=True)
    booking_reference = Column(String(100), nullable=True)
    transport_doc_number = Column(String(100), nullable=True)  # B/L or AWB Number

    # Containers list JSON e.g. [{"container_no": "MSCU1234567", "seal_no": "PK9876", "size_type": "40HC"}]
    container_numbers = Column(JSON, nullable=True, default=list)

    # Route & Ports
    port_of_loading = Column(String(255), nullable=True)
    port_of_discharge = Column(String(255), nullable=True)
    final_destination = Column(String(255), nullable=True)

    # Schedule Timestamps
    etd = Column(DateTime, nullable=True)  # Estimated Time of Departure
    eta = Column(DateTime, nullable=True)  # Estimated Time of Arrival
    atd = Column(DateTime, nullable=True)  # Actual Time of Departure
    ata = Column(DateTime, nullable=True)  # Actual Time of Arrival

    # Cargo Metrics
    packages_count = Column(Integer, nullable=True)
    package_type = Column(String(100), nullable=True, default="Cartons")
    gross_weight_kg = Column(Numeric(14, 2), nullable=True)
    net_weight_kg = Column(Numeric(14, 2), nullable=True)
    volume_cbm = Column(Numeric(14, 3), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    deal = relationship("Deal", backref="shipments")
    milestones = relationship(
        "ShipmentMilestone",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentMilestone.planned_date",
    )


class ShipmentMilestone(Base):
    __tablename__ = "shipment_milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    milestone_type = Column(
        SQLEnum(MilestoneType, name="milestonetype"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)

    planned_date = Column(DateTime, nullable=False)
    actual_date = Column(DateTime, nullable=True)
    status = Column(
        SQLEnum(MilestoneStatus, name="milestonestatus"),
        nullable=False,
        default=MilestoneStatus.PENDING,
    )
    variance_days = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    shipment = relationship("Shipment", back_populates="milestones")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_type = Column(
        SQLEnum(PaymentType, name="paymenttype"),
        nullable=False,
        default=PaymentType.BANK_TRANSFER,
    )
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")

    # Realized Exchange Difference tracking (FR-PAY-05)
    realized_exchange_rate = Column(Numeric(12, 4), nullable=True)  # e.g., 278.50 PKR/USD
    settlement_amount_pkr = Column(Numeric(16, 2), nullable=True)
    realized_fx_gain_loss = Column(Numeric(14, 2), nullable=True, default=Decimal("0.00"))

    payment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    bank_reference = Column(String(255), nullable=True)  # SWIFT MT103 / e-Form R ref
    bank_charges = Column(Numeric(10, 2), nullable=True, default=Decimal("0.00"))
    bank_name = Column(String(255), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    deal = relationship("Deal", backref="payment_transactions")
