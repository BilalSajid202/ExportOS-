"""Create artifacts table for inbound inquiries and document storage

Revision ID: 0003_create_artifacts_table
Revises: 0002_products_inventory_deals
Create Date: 2026-09-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0003_create_artifacts_table"
down_revision: Union[str, None] = "0002_products_inventory_deals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Artifacts ─────────────────────────────────────────────
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", sa.String(length=50), server_default="INBOUND_INQUIRY", nullable=False),
        sa.Column("channel", sa.String(length=50), server_default="FILE_UPLOAD", nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), server_default="application/octet-stream", nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("sender_info", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_artifacts_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_artifacts_deal_id_deals",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_artifacts_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_artifacts"),
    )
    op.create_index("ix_artifacts_organisation_id", "artifacts", ["organisation_id"], unique=False)
    op.create_index("ix_artifacts_deal_id", "artifacts", ["deal_id"], unique=False)
    op.create_index("ix_artifacts_sha256_hash", "artifacts", ["sha256_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_artifacts_sha256_hash", table_name="artifacts")
    op.drop_index("ix_artifacts_deal_id", table_name="artifacts")
    op.drop_index("ix_artifacts_organisation_id", table_name="artifacts")
    op.drop_table("artifacts")
