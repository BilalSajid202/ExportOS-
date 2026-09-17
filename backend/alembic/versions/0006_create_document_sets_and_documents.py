"""Create document_sets and generated_documents tables

Revision ID: 0006_create_document_sets
Revises: 0005_costing_quotes_and_audit
Create Date: 2026-09-17 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "0006_create_document_sets"
down_revision: Union[str, None] = "0005_costing_quotes_and_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Document Sets Table ────────────────────────────────────
    op.create_table(
        "document_sets",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_document_sets_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_document_sets_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_sets"),
    )
    op.create_index("ix_document_sets_organisation_id", "document_sets", ["organisation_id"])
    op.create_index("ix_document_sets_deal_id", "document_sets", ["deal_id"])

    # ── Generated Documents Table ──────────────────────────────
    op.create_table(
        "generated_documents",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_set_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("document_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_json", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="DRAFT", nullable=False),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_generated_documents_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_generated_documents_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_set_id"],
            ["document_sets.id"],
            name="fk_generated_documents_document_set_id_document_sets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_generated_documents_approved_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generated_documents"),
    )
    op.create_index("ix_generated_documents_organisation_id", "generated_documents", ["organisation_id"])
    op.create_index("ix_generated_documents_deal_id", "generated_documents", ["deal_id"])
    op.create_index("ix_generated_documents_document_set_id", "generated_documents", ["document_set_id"])


def downgrade() -> None:
    op.drop_table("generated_documents")
    op.drop_table("document_sets")
