"""Create extraction_results table for AI interpretations

Revision ID: 0004_create_extractions_table
Revises: 0003_create_artifacts_table
Create Date: 2026-09-17 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "0004_create_extractions_table"
down_revision: Union[str, None] = "0003_create_artifacts_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extraction Results ─────────────────────────────────────
    op.create_table(
        "extraction_results",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.String(length=100), server_default="tradeloop-ai-extractor-v1", nullable=False),
        sa.Column("model_version", sa.String(length=50), server_default="1.1", nullable=False),
        sa.Column("extracted_data", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="PENDING_REVIEW", nullable=False),
        sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_extraction_results_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_extraction_results_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_extraction_results_artifact_id_artifacts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_extraction_results_reviewed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_results"),
    )
    op.create_index("ix_extraction_results_organisation_id", "extraction_results", ["organisation_id"], unique=False)
    op.create_index("ix_extraction_results_deal_id", "extraction_results", ["deal_id"], unique=False)
    op.create_index("ix_extraction_results_artifact_id", "extraction_results", ["artifact_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_extraction_results_artifact_id", table_name="extraction_results")
    op.drop_index("ix_extraction_results_deal_id", table_name="extraction_results")
    op.drop_index("ix_extraction_results_organisation_id", table_name="extraction_results")
    op.drop_table("extraction_results")
