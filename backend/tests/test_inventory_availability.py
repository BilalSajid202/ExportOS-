"""
Unit tests for deterministic inventory availability math.

Test cases from ExportOS Implementation Documentation Phase 3:
  Stock=100, Reserved=20, Requested=50 → AVAILABLE, Available=80
  Stock=100, Reserved=80, Requested=50 → PARTIALLY_AVAILABLE, Available=20, Shortfall=30
"""

from decimal import Decimal

from app.models.inventory import AvailabilityStatus
from app.services.inventory import compute_availability


def test_fully_available():
    available, shortfall, status = compute_availability(
        current=Decimal("100"),
        reserved=Decimal("20"),
        requested=Decimal("50"),
    )
    assert available == Decimal("80")
    assert shortfall == Decimal("0")
    assert status == AvailabilityStatus.AVAILABLE


def test_partially_available():
    available, shortfall, status = compute_availability(
        current=Decimal("100"),
        reserved=Decimal("80"),
        requested=Decimal("50"),
    )
    assert available == Decimal("20")
    assert shortfall == Decimal("30")
    assert status == AvailabilityStatus.PARTIALLY_AVAILABLE


def test_unavailable():
    available, shortfall, status = compute_availability(
        current=Decimal("100"),
        reserved=Decimal("100"),
        requested=Decimal("50"),
    )
    assert available == Decimal("0")
    assert shortfall == Decimal("50")
    assert status == AvailabilityStatus.UNAVAILABLE


def test_exact_match():
    available, shortfall, status = compute_availability(
        current=Decimal("3000"),
        reserved=Decimal("500"),
        requested=Decimal("2500"),
    )
    assert available == Decimal("2500")
    assert shortfall == Decimal("0")
    assert status == AvailabilityStatus.AVAILABLE


def test_inventory_transaction_response_with_uuid_reference_id():
    import uuid
    from datetime import datetime, timezone
    from app.models.inventory import InventoryTransactionType
    from app.schemas.inventory import InventoryTransactionResponse

    tx_resp = InventoryTransactionResponse(
        id=uuid.uuid4(),
        organisation_id=uuid.uuid4(),
        inventory_item_id=uuid.uuid4(),
        transaction_type=InventoryTransactionType.RESERVATION,
        quantity=Decimal("50"),
        reference_type="RESERVATION",
        reference_id=uuid.uuid4(),
        notes="Test reservation",
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        sku="TEST-SKU",
        product_name="Test Product",
    )
    assert tx_resp.reference_id is not None
    assert isinstance(tx_resp.reference_id, uuid.UUID)

