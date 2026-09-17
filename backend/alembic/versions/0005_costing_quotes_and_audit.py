"""Create cost_components, deal_quotes, and audit_entries tables

Revision ID: 0005_costing_quotes_and_audit
Revises: 0004_create_extractions_table
Create Date: 2026-09-17 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "0005_costing_quotes_and_audit"
down_revision: Union[str, None] = "0004_create_extractions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Cost Components Table ──────────────────────────────────
    op.create_table(
        "cost_components",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cost_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_cost_components_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_cost_components_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cost_components"),
    )
    op.create_index("ix_cost_components_organisation_id", "cost_components", ["organisation_id"])
    op.create_index("ix_cost_components_deal_id", "cost_components", ["deal_id"])

    # ── Deal Quotes Table ──────────────────────────────────────
    op.create_table(
        "deal_quotes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("incoterm", sa.String(length=10), nullable=False),
        sa.Column("incoterm_place", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("base_cost", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("logistics_cost", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("margin_percentage", sa.Numeric(precision=6, scale=2), server_default="15.00", nullable=False),
        sa.Column("margin_amount", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("total_quote_price", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_deal_quotes_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_deal_quotes_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_deal_quotes_approved_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deal_quotes"),
    )
    op.create_index("ix_deal_quotes_organisation_id", "deal_quotes", ["organisation_id"])
    op.create_index("ix_deal_quotes_deal_id", "deal_quotes", ["deal_id"])

    # ── Audit Entries Table ────────────────────────────────────
    op.create_table(
        "audit_entries",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("from_state", sa.String(length=50), nullable=True),
        sa.Column("to_state", sa.String(length=50), nullable=True),
        sa.Column("details", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_audit_entries_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_audit_entries_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_entries_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_entries"),
    )
    op.create_index("ix_audit_entries_organisation_id", "audit_entries", ["organisation_id"])
    op.create_index("ix_audit_entries_deal_id", "audit_entries", ["deal_id"])


def downgrade() -> None:
    op.drop_table("audit_entries")
    op.drop_table("deal_quotes")
    op.drop_table("cost_components")
