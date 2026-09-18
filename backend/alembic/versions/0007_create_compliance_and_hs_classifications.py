"""Create compliance_checks and hs_code_classifications tables

Revision ID: 0007_compliance_and_hs
Revises: 0006_create_document_sets
Create Date: 2026-09-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0007_compliance_and_hs"
down_revision: Union[str, None] = "0006_create_document_sets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Compliance Checks Table ─────────────────────────────────
    op.create_table(
        "compliance_checks",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(length=60), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("authority", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="NOT_STARTED", nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("responsible_role", sa.String(length=50), server_default="DOCUMENTATION_OFFICER", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.String(length=255), nullable=True),
        sa.Column("completed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_compliance_checks_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_compliance_checks_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by"],
            ["users.id"],
            name="fk_compliance_checks_completed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_compliance_checks"),
    )
    op.create_index("ix_compliance_checks_organisation_id", "compliance_checks", ["organisation_id"])
    op.create_index("ix_compliance_checks_deal_id", "compliance_checks", ["deal_id"])
    op.create_index("ix_compliance_checks_rule_code", "compliance_checks", ["rule_code"])

    # ── HS Code Classifications Table ───────────────────────────
    op.create_table(
        "hs_code_classifications",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_code", sa.String(length=20), nullable=False),
        sa.Column("confirmed_code", sa.String(length=20), nullable=True),
        sa.Column("heading_title", sa.String(length=255), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=2), server_default="0.85", nullable=False),
        sa.Column("tariff_source", sa.String(length=255), server_default="Pakistan Customs Tariff (PCT) 2024-25 / WCO Harmonized System", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="SUGGESTED", nullable=False),
        sa.Column("confirmed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_hs_classifications_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_hs_classifications_deal_id_deals",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_hs_classifications_product_id_products",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"],
            ["users.id"],
            name="fk_hs_classifications_confirmed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hs_code_classifications"),
    )
    op.create_index("ix_hs_classifications_organisation_id", "hs_code_classifications", ["organisation_id"])
    op.create_index("ix_hs_classifications_deal_id", "hs_code_classifications", ["deal_id"])
    op.create_index("ix_hs_classifications_product_id", "hs_code_classifications", ["product_id"])


def downgrade() -> None:
    op.drop_table("hs_code_classifications")
    op.drop_table("compliance_checks")
