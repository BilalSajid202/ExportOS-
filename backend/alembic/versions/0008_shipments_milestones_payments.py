"""Create shipments, shipment_milestones, and payment_transactions tables

Revision ID: 0008_shipments_and_payments
Revises: 0007_compliance_and_hs
Create Date: 2026-09-18 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


revision: str = "0008_shipments_and_payments"
down_revision: Union[str, None] = "0007_compliance_and_hs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Shipments Table ─────────────────────────────────────────
    op.create_table(
        "shipments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_number", sa.String(length=100), nullable=False),
        sa.Column("transport_mode", sa.String(length=50), server_default="OCEAN_FCL", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("freight_terms", sa.String(length=50), server_default="FREIGHT_PREPAID", nullable=False),
        sa.Column("carrier_name", sa.String(length=255), nullable=True),
        sa.Column("vessel_or_flight", sa.String(length=255), nullable=True),
        sa.Column("voyage_number", sa.String(length=100), nullable=True),
        sa.Column("booking_reference", sa.String(length=100), nullable=True),
        sa.Column("transport_doc_number", sa.String(length=100), nullable=True),
        sa.Column("container_numbers", JSON, nullable=True),
        sa.Column("port_of_loading", sa.String(length=255), nullable=True),
        sa.Column("port_of_discharge", sa.String(length=255), nullable=True),
        sa.Column("final_destination", sa.String(length=255), nullable=True),
        sa.Column("etd", sa.DateTime(), nullable=True),
        sa.Column("eta", sa.DateTime(), nullable=True),
        sa.Column("atd", sa.DateTime(), nullable=True),
        sa.Column("ata", sa.DateTime(), nullable=True),
        sa.Column("packages_count", sa.Integer(), nullable=True),
        sa.Column("package_type", sa.String(length=100), server_default="Cartons", nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("net_weight_kg", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("volume_cbm", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_number"),
    )
    op.create_index(op.f("ix_shipments_deal_id"), "shipments", ["deal_id"], unique=False)
    op.create_index(op.f("ix_shipments_organisation_id"), "shipments", ["organisation_id"], unique=False)
    op.create_index(op.f("ix_shipments_status"), "shipments", ["status"], unique=False)
    op.create_index(op.f("ix_shipments_tracking_number"), "shipments", ["tracking_number"], unique=False)

    # ── Shipment Milestones Table ───────────────────────────────
    op.create_table(
        "shipment_milestones",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("shipment_id", UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("planned_date", sa.DateTime(), nullable=False),
        sa.Column("actual_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column("variance_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipment_milestones_shipment_id"), "shipment_milestones", ["shipment_id"], unique=False)

    # ── Payment Transactions Table ──────────────────────────────
    op.create_table(
        "payment_transactions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payment_type", sa.String(length=50), server_default="BANK_TRANSFER", nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="USD", nullable=False),
        sa.Column("realized_exchange_rate", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("settlement_amount_pkr", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("realized_fx_gain_loss", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=True),
        sa.Column("payment_date", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("bank_reference", sa.String(length=255), nullable=True),
        sa.Column("bank_charges", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_transactions_deal_id"), "payment_transactions", ["deal_id"], unique=False)
    op.create_index(op.f("ix_payment_transactions_organisation_id"), "payment_transactions", ["organisation_id"], unique=False)


def downgrade() -> None:
    op.drop_table("payment_transactions")
    op.drop_table("shipment_milestones")
    op.drop_table("shipments")
