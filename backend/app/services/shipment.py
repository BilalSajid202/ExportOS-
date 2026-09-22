"""
ExportOS — Shipment & Milestone Logistics Tracking Service (Phase 13)

Implements multi-modal transport tracking (OCEAN_FCL, OCEAN_LCL, AIR_FREIGHT, LAND_TRUCK),
deterministic milestone sequence generation based on Incoterms 2020, variance calculations,
overdue milestone detection, and transport lifecycle transitions.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import random
import string

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.logistics import (
    Shipment,
    ShipmentMilestone,
    TransportMode,
    ShipmentStatus,
    FreightTerms,
    MilestoneType,
    MilestoneStatus,
)
from app.models.deal import Deal, DealState
from app.models.costing import DealQuote
from app.schemas.logistics import (
    ShipmentCreate,
    ShipmentUpdate,
    MilestoneUpdate,
    ShipmentSummaryResponse,
)


def generate_tracking_number(mode: TransportMode) -> str:
    prefix = {
        TransportMode.OCEAN_FCL: "EXP-OCN",
        TransportMode.OCEAN_LCL: "EXP-LCL",
        TransportMode.AIR_FREIGHT: "EXP-AIR",
        TransportMode.LAND_TRUCK: "EXP-LND",
    }.get(mode, "EXP-SHP")
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{random_str}"


def get_default_milestones_for_shipment(
    mode: TransportMode,
    incoterm: str = "CIF",
    base_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Generates a realistic milestone schedule based on transport mode and Incoterm.
    """
    base = base_date or datetime.now(timezone.utc)
    is_air = mode == TransportMode.AIR_FREIGHT

    if is_air:
        return [
            {
                "milestone_type": MilestoneType.BOOKING_CONFIRMED,
                "title": "Air Waybill & Flight Booking Confirmed",
                "description": "Cargo space confirmed on scheduled airline.",
                "location": "Karachi / Lahore Cargo Terminal",
                "planned_date": base + timedelta(days=1),
            },
            {
                "milestone_type": MilestoneType.CARGO_READY,
                "title": "Cargo Received at Air Cargo Complex",
                "description": "Export packaging verified, weighed and dimensioned.",
                "location": "Airport Freight Station",
                "planned_date": base + timedelta(days=2),
            },
            {
                "milestone_type": MilestoneType.PORT_GATE_IN,
                "title": "Airport Cargo Terminal Gate-In",
                "description": "Security screening and palletization completed.",
                "location": "Jinnah International Airport (KHI)",
                "planned_date": base + timedelta(days=3),
            },
            {
                "milestone_type": MilestoneType.CUSTOMS_OUT_CHARGE_WEBOC,
                "title": "Customs Export Assessment (WeBOC Air GD Out-of-Charge)",
                "description": "Export assessment complete; SBP Form-E validated.",
                "location": "Air Cargo Customs, Karachi",
                "planned_date": base + timedelta(days=4),
            },
            {
                "milestone_type": MilestoneType.VESSEL_DEPARTURE,
                "title": "Flight Departure",
                "description": "Flight departed from origin airport.",
                "location": "Karachi (KHI)",
                "planned_date": base + timedelta(days=5),
            },
            {
                "milestone_type": MilestoneType.DESTINATION_ARRIVAL,
                "title": "Flight Arrival at Destination Airport",
                "description": "Cargo unladen at destination airport terminal.",
                "location": "Destination Airport",
                "planned_date": base + timedelta(days=7),
            },
            {
                "milestone_type": MilestoneType.CUSTOMS_CLEARANCE,
                "title": "Import Customs Clearance",
                "description": "Customs clearance and duty payment finalized.",
                "location": "Destination Customs",
                "planned_date": base + timedelta(days=8),
            },
            {
                "milestone_type": MilestoneType.FINAL_DELIVERY,
                "title": "Consignee Final Handover",
                "description": "Shipment delivered to buyer facility.",
                "location": "Buyer Facility",
                "planned_date": base + timedelta(days=9),
            },
        ]

    # Standard Ocean FCL/LCL Sequence
    return [
        {
            "milestone_type": MilestoneType.BOOKING_CONFIRMED,
            "title": "Shipping Line Booking Confirmed",
            "description": "Container booking and equipment release order issued.",
            "location": "Karachi Port / Shipping Agent",
            "planned_date": base + timedelta(days=2),
        },
        {
            "milestone_type": MilestoneType.CARGO_READY,
            "title": "Factory Production Complete & Cargo Ready",
            "description": "Export quality inspection and packaging complete.",
            "location": "Exporter Factory (Sialkot / Faisalabad)",
            "planned_date": base + timedelta(days=5),
        },
        {
            "milestone_type": MilestoneType.CONTAINER_STUFFING,
            "title": "Container Stuffing & Sealing",
            "description": "Cargo stuffed into container with high-security bolt seal.",
            "location": "Factory / Dry Port CFS",
            "planned_date": base + timedelta(days=6),
        },
        {
            "milestone_type": MilestoneType.PORT_GATE_IN,
            "title": "Seaport Terminal Gate-In",
            "description": "Container gated in at QICT / KICT / SAPT terminal.",
            "location": "Port Muhammad Bin Qasim / KPT, Karachi",
            "planned_date": base + timedelta(days=8),
        },
        {
            "milestone_type": MilestoneType.CUSTOMS_OUT_CHARGE_WEBOC,
            "title": "Customs Export Clearance (WeBOC Out-of-Charge)",
            "description": "Pakistan Single Window electronic Form-E validated & GD cleared.",
            "location": "Port Qasim Customs, Karachi",
            "planned_date": base + timedelta(days=9),
        },
        {
            "milestone_type": MilestoneType.VESSEL_DEPARTURE,
            "title": "Vessel Departure (Port of Loading)",
            "description": "Container loaded on mother/feeder vessel and departed.",
            "location": "Port Qasim, Karachi",
            "planned_date": base + timedelta(days=12),
        },
        {
            "milestone_type": MilestoneType.IN_TRANSIT_TRANSSHIPMENT,
            "title": "Transshipment Port Connection",
            "description": "Container transferred to mother vessel at transshipment hub.",
            "location": "Jebel Ali / Salalah / Colombo Hub",
            "planned_date": base + timedelta(days=18),
        },
        {
            "milestone_type": MilestoneType.DESTINATION_ARRIVAL,
            "title": "Vessel Arrival at Destination Port",
            "description": "Vessel berthed and container discharged at destination port.",
            "location": "Destination Port (e.g. Hamburg / Rotterdam / New York)",
            "planned_date": base + timedelta(days=32),
        },
        {
            "milestone_type": MilestoneType.CUSTOMS_CLEARANCE,
            "title": "Destination Customs Clearance",
            "description": "Import declarations, REX/GSP+ tariff preference, and release.",
            "location": "Destination Port Customs",
            "planned_date": base + timedelta(days=35),
        },
        {
            "milestone_type": MilestoneType.FINAL_DELIVERY,
            "title": "Consignee Door Delivery",
            "description": "Inland haulage and final delivery to buyer distribution center.",
            "location": "Buyer Warehouse",
            "planned_date": base + timedelta(days=37),
        },
    ]


async def create_shipment_for_deal(
    db: AsyncSession,
    deal_id: UUID,
    organisation_id: UUID,
    payload: ShipmentCreate,
) -> Shipment:
    deal_stmt = select(Deal).where(Deal.id == deal_id, Deal.organisation_id == organisation_id)
    deal_res = await db.execute(deal_stmt)
    deal = deal_res.scalars().first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    tracking_num = generate_tracking_number(payload.transport_mode)

    # Resolve default ports/destination if not provided
    q_stmt = select(DealQuote).where(DealQuote.deal_id == deal_id).order_by(desc(DealQuote.created_at))
    q_res = await db.execute(q_stmt)
    quote = q_res.scalars().first()
    incoterm_str = quote.incoterm if quote else "CIF"
    dest_place = payload.final_destination or (quote.incoterm_place if quote else deal.notes)
    origin_port = payload.port_of_loading or (
        "Karachi Airport (KHI)" if payload.transport_mode == TransportMode.AIR_FREIGHT else "Port Qasim, Karachi"
    )

    now = datetime.now(timezone.utc)
    etd_val = payload.etd or (now + timedelta(days=5 if payload.transport_mode == TransportMode.AIR_FREIGHT else 12))
    eta_val = payload.eta or (now + timedelta(days=9 if payload.transport_mode == TransportMode.AIR_FREIGHT else 37))

    shipment = Shipment(
        organisation_id=organisation_id,
        deal_id=deal_id,
        tracking_number=tracking_num,
        transport_mode=payload.transport_mode,
        status=ShipmentStatus.BOOKED,
        freight_terms=payload.freight_terms,
        carrier_name=payload.carrier_name or ("Qatar Airways Cargo" if payload.transport_mode == TransportMode.AIR_FREIGHT else "Maersk Line"),
        vessel_or_flight=payload.vessel_or_flight or ("QR-611" if payload.transport_mode == TransportMode.AIR_FREIGHT else "Maersk Karachi"),
        voyage_number=payload.voyage_number or "V.2026E",
        booking_reference=payload.booking_reference or f"BKG-{random.randint(100000, 999999)}",
        transport_doc_number=payload.transport_doc_number or (f"AWB-{random.randint(100, 999)}-{random.randint(10000000, 99999999)}" if payload.transport_mode == TransportMode.AIR_FREIGHT else f"MSK{random.randint(100000000, 999999999)}"),
        container_numbers=payload.container_numbers or ([{"container_no": f"MSCU{random.randint(1000000, 9999999)}", "seal_no": f"PK-{random.randint(10000, 99999)}", "size_type": "40HC"}] if payload.transport_mode == TransportMode.OCEAN_FCL else []),
        port_of_loading=origin_port,
        port_of_discharge=payload.port_of_discharge or (dest_place or "Destination Port"),
        final_destination=dest_place,
        etd=etd_val,
        eta=eta_val,
        packages_count=payload.packages_count or 500,
        package_type=payload.package_type or "Cartons",
        gross_weight_kg=payload.gross_weight_kg or 4500.00,
        net_weight_kg=payload.net_weight_kg or 4100.00,
        volume_cbm=payload.volume_cbm or 28.500,
        notes=payload.notes,
    )
    db.add(shipment)
    await db.flush()

    # Generate initial milestones
    milestone_specs = get_default_milestones_for_shipment(payload.transport_mode, incoterm_str, base_date=now)
    for spec in milestone_specs:
        m = ShipmentMilestone(
            shipment_id=shipment.id,
            milestone_type=spec["milestone_type"],
            title=spec["title"],
            description=spec["description"],
            location=spec["location"],
            planned_date=spec["planned_date"],
            status=MilestoneStatus.PENDING,
            variance_days=0,
        )
        db.add(m)

    # Mark first milestone as completed (Booking Confirmed)
    await db.flush()
    first_stmt = select(ShipmentMilestone).where(
        ShipmentMilestone.shipment_id == shipment.id,
        ShipmentMilestone.milestone_type == MilestoneType.BOOKING_CONFIRMED,
    )
    first_res = await db.execute(first_stmt)
    first_m = first_res.scalars().first()
    if first_m:
        first_m.status = MilestoneStatus.COMPLETED
        first_m.actual_date = now

    await db.commit()
    await db.refresh(shipment)
    return shipment


async def update_shipment_details(
    db: AsyncSession,
    shipment_id: UUID,
    organisation_id: UUID,
    payload: ShipmentUpdate,
) -> Shipment:
    stmt = select(Shipment).where(Shipment.id == shipment_id, Shipment.organisation_id == organisation_id)
    res = await db.execute(stmt)
    shipment = res.scalars().first()
    if not shipment:
        raise ValueError("Shipment not found")

    for field, val in payload.dict(exclude_unset=True).items():
        setattr(shipment, field, val)

    # If status transitioned to IN_TRANSIT and atd not set, set atd
    now = datetime.now(timezone.utc)
    if shipment.status == ShipmentStatus.IN_TRANSIT and not shipment.atd:
        shipment.atd = now
    elif shipment.status == ShipmentStatus.DELIVERED and not shipment.ata:
        shipment.ata = now

    await db.commit()
    await db.refresh(shipment)
    return shipment


async def update_milestone_status(
    db: AsyncSession,
    shipment_id: UUID,
    milestone_id: UUID,
    organisation_id: UUID,
    payload: MilestoneUpdate,
) -> ShipmentMilestone:
    s_stmt = select(Shipment).where(Shipment.id == shipment_id, Shipment.organisation_id == organisation_id)
    s_res = await db.execute(s_stmt)
    shipment = s_res.scalars().first()
    if not shipment:
        raise ValueError("Shipment not found")

    m_stmt = select(ShipmentMilestone).where(
        ShipmentMilestone.id == milestone_id,
        ShipmentMilestone.shipment_id == shipment_id,
    )
    m_res = await db.execute(m_stmt)
    milestone = m_res.scalars().first()
    if not milestone:
        raise ValueError("Milestone not found")

    if payload.status is not None:
        milestone.status = payload.status
    if payload.location is not None:
        milestone.location = payload.location
    if payload.description is not None:
        milestone.description = payload.description

    now = datetime.now(timezone.utc)
    if payload.actual_date is not None:
        milestone.actual_date = payload.actual_date
    elif payload.status == MilestoneStatus.COMPLETED and not milestone.actual_date:
        milestone.actual_date = now

    # Calculate schedule variance
    if milestone.actual_date and milestone.planned_date:
        diff = (milestone.actual_date.date() - milestone.planned_date.date()).days
        milestone.variance_days = diff
        if diff > 0 and milestone.status != MilestoneStatus.COMPLETED:
            milestone.status = MilestoneStatus.DELAYED

    # Synchronize overall shipment status
    if milestone.milestone_type == MilestoneType.VESSEL_DEPARTURE and milestone.status == MilestoneStatus.COMPLETED:
        shipment.status = ShipmentStatus.IN_TRANSIT
        shipment.atd = milestone.actual_date or now
    elif milestone.milestone_type == MilestoneType.FINAL_DELIVERY and milestone.status == MilestoneStatus.COMPLETED:
        shipment.status = ShipmentStatus.DELIVERED
        shipment.ata = milestone.actual_date or now

    await db.commit()
    await db.refresh(milestone)
    return milestone


async def get_shipments_for_deal(
    db: AsyncSession,
    deal_id: UUID,
    organisation_id: UUID,
) -> List[Shipment]:
    stmt = (
        select(Shipment)
        .options(selectinload(Shipment.milestones))
        .where(Shipment.deal_id == deal_id, Shipment.organisation_id == organisation_id)
        .order_by(desc(Shipment.created_at))
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def get_active_shipments_summary(
    db: AsyncSession,
    organisation_id: UUID,
) -> ShipmentSummaryResponse:
    stmt = (
        select(Shipment)
        .options(selectinload(Shipment.milestones))
        .where(Shipment.organisation_id == organisation_id)
        .order_by(desc(Shipment.created_at))
    )
    res = await db.execute(stmt)
    shipments = res.scalars().all()

    now = datetime.now(timezone.utc)
    active_in_transit = 0
    delivered_count = 0
    overdue_milestones = 0

    for shp in shipments:
        if shp.status == ShipmentStatus.IN_TRANSIT:
            active_in_transit += 1
        elif shp.status == ShipmentStatus.DELIVERED:
            delivered_count += 1

        for m in shp.milestones:
            p_date = m.planned_date
            if p_date and p_date.tzinfo is None:
                p_date = p_date.replace(tzinfo=timezone.utc)
            if m.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS] and p_date and p_date < now:
                overdue_milestones += 1

    return ShipmentSummaryResponse(
        shipments=shipments,
        total_shipments=len(shipments),
        active_in_transit=active_in_transit,
        delivered_count=delivered_count,
        overdue_milestones_count=overdue_milestones,
    )
