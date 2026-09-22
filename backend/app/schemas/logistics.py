from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Dict
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.logistics import (
    TransportMode,
    ShipmentStatus,
    FreightTerms,
    MilestoneType,
    MilestoneStatus,
    PaymentType,
    PaymentStatus,
)


class ContainerInfo(BaseModel):
    container_no: str
    seal_no: Optional[str] = None
    size_type: Optional[str] = "40HC"  # 20GP, 40GP, 40HC, 45HC, LCL


class MilestoneBase(BaseModel):
    milestone_type: MilestoneType
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    planned_date: datetime
    actual_date: Optional[datetime] = None
    status: MilestoneStatus = MilestoneStatus.PENDING


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    actual_date: Optional[datetime] = None
    status: Optional[MilestoneStatus] = None
    location: Optional[str] = None
    description: Optional[str] = None


class MilestoneResponse(MilestoneBase):
    id: UUID
    shipment_id: UUID
    variance_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentBase(BaseModel):
    transport_mode: TransportMode = TransportMode.OCEAN_FCL
    freight_terms: FreightTerms = FreightTerms.FREIGHT_PREPAID
    carrier_name: Optional[str] = None
    vessel_or_flight: Optional[str] = None
    voyage_number: Optional[str] = None
    booking_reference: Optional[str] = None
    transport_doc_number: Optional[str] = None
    container_numbers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    final_destination: Optional[str] = None
    etd: Optional[datetime] = None
    eta: Optional[datetime] = None
    atd: Optional[datetime] = None
    ata: Optional[datetime] = None
    packages_count: Optional[int] = None
    package_type: Optional[str] = "Cartons"
    gross_weight_kg: Optional[Decimal] = None
    net_weight_kg: Optional[Decimal] = None
    volume_cbm: Optional[Decimal] = None
    notes: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentUpdate(BaseModel):
    transport_mode: Optional[TransportMode] = None
    status: Optional[ShipmentStatus] = None
    freight_terms: Optional[FreightTerms] = None
    carrier_name: Optional[str] = None
    vessel_or_flight: Optional[str] = None
    voyage_number: Optional[str] = None
    booking_reference: Optional[str] = None
    transport_doc_number: Optional[str] = None
    container_numbers: Optional[List[Dict[str, Any]]] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    final_destination: Optional[str] = None
    etd: Optional[datetime] = None
    eta: Optional[datetime] = None
    atd: Optional[datetime] = None
    ata: Optional[datetime] = None
    packages_count: Optional[int] = None
    package_type: Optional[str] = None
    gross_weight_kg: Optional[Decimal] = None
    net_weight_kg: Optional[Decimal] = None
    volume_cbm: Optional[Decimal] = None
    notes: Optional[str] = None


class ShipmentResponse(ShipmentBase):
    id: UUID
    organisation_id: UUID
    deal_id: UUID
    tracking_number: str
    status: ShipmentStatus
    created_at: datetime
    updated_at: datetime
    milestones: List[MilestoneResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ShipmentSummaryResponse(BaseModel):
    shipments: List[ShipmentResponse]
    total_shipments: int
    active_in_transit: int
    delivered_count: int
    overdue_milestones_count: int


# ── Payment Schemas ──────────────────────────────────────────

class PaymentCreate(BaseModel):
    payment_type: PaymentType = PaymentType.BANK_TRANSFER
    amount: Decimal
    currency: str = "USD"
    realized_exchange_rate: Optional[Decimal] = None  # e.g., 278.50 PKR per USD
    payment_date: Optional[datetime] = None
    bank_reference: Optional[str] = None
    bank_charges: Optional[Decimal] = Decimal("0.00")
    bank_name: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: UUID
    organisation_id: UUID
    deal_id: UUID
    payment_type: PaymentType
    amount: Decimal
    currency: str
    realized_exchange_rate: Optional[Decimal]
    settlement_amount_pkr: Optional[Decimal]
    realized_fx_gain_loss: Decimal
    payment_date: datetime
    bank_reference: Optional[str]
    bank_charges: Decimal
    bank_name: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DealPaymentSummary(BaseModel):
    deal_id: UUID
    buyer_name: str
    invoice_currency: str
    total_invoice_amount: Decimal
    total_paid_amount: Decimal
    outstanding_balance: Decimal
    payment_status: PaymentStatus
    realized_fx_gain_loss_total: Decimal
    advance_amount_received: Decimal
    sbp_realization_deadline: Optional[datetime] = None
    sbp_days_remaining: Optional[int] = None
    is_sbp_at_risk: bool = False
    is_sbp_overdue: bool = False
    transactions: List[PaymentResponse] = Field(default_factory=list)


class ReceivablesAgingDealItem(BaseModel):
    deal_id: UUID
    reference: str
    buyer_name: str
    total_invoice: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    currency: str
    payment_status: PaymentStatus
    days_since_shipment: Optional[int] = None
    sbp_days_remaining: Optional[int] = None
    aging_bucket: str  # CURRENT, 1_30, 31_60, 61_90, 91_120_SBP_ALERT, OVERDUE_120_PLUS


class ReceivablesAgingReport(BaseModel):
    total_receivables_usd: Decimal
    current_not_due: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_91_120_sbp_risk: Decimal
    overdue_120_plus: Decimal
    deals: List[ReceivablesAgingDealItem]
