"""Create products, deals, and inventory tables

Revision ID: 0002_products_inventory_deals
Revises: 0001_create_orgs_and_users
Create Date: 2026-09-17 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0002_products_inventory_deals"
down_revision: Union[str, None] = "0001_create_orgs_and_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Products ──────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=20), server_default="PCS", nullable=False),
        sa.Column("selling_currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("default_hs_code", sa.String(length=20), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("carton_capacity", sa.Integer(), nullable=True),
        sa.Column("base_cost", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_products_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("organisation_id", "sku", name="uq_products_organisation_id_sku"),
    )
    op.create_index("ix_products_organisation_id", "products", ["organisation_id"], unique=False)
    op.create_index("ix_products_sku", "products", ["sku"], unique=False)

    # ── Deals ─────────────────────────────────────────────────
    op.create_table(
        "deals",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=50), nullable=False),
        sa.Column("buyer_name", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=50), server_default="INQUIRY", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_deals_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_deals_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deals"),
    )
    op.create_index("ix_deals_organisation_id", "deals", ["organisation_id"], unique=False)
    op.create_index("ix_deals_reference", "deals", ["reference"], unique=False)

    op.create_table(
        "deal_line_items",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_deal_line_items_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_deal_line_items_deal_id_deals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_deal_line_items_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deal_line_items"),
    )
    op.create_index("ix_deal_line_items_organisation_id", "deal_line_items", ["organisation_id"], unique=False)
    op.create_index("ix_deal_line_items_deal_id", "deal_line_items", ["deal_id"], unique=False)
    op.create_index("ix_deal_line_items_product_id", "deal_line_items", ["product_id"], unique=False)

    # ── Inventory ─────────────────────────────────────────────
    op.create_table(
        "inventory_items",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("current_quantity", sa.Numeric(precision=18, scale=3), server_default="0", nullable=False),
        sa.Column("reserved_quantity", sa.Numeric(precision=18, scale=3), server_default="0", nullable=False),
        sa.Column("reorder_level", sa.Numeric(precision=18, scale=3), server_default="0", nullable=False),
        sa.Column("unit_of_measure", sa.String(length=20), server_default="PCS", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_inventory_items_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_inventory_items_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint("product_id", name="uq_inventory_items_product_id"),
    )
    op.create_index("ix_inventory_items_organisation_id", "inventory_items", ["organisation_id"], unique=False)
    op.create_index("ix_inventory_items_product_id", "inventory_items", ["product_id"], unique=False)
    op.create_index("ix_inventory_items_sku", "inventory_items", ["sku"], unique=False)

    op.create_table(
        "inventory_transactions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_inventory_transactions_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_inventory_transactions_inventory_item_id_inventory_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_inventory_transactions_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_transactions"),
    )
    op.create_index(
        "ix_inventory_transactions_organisation_id",
        "inventory_transactions",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_transactions_inventory_item_id",
        "inventory_transactions",
        ["inventory_item_id"],
        unique=False,
    )

    op.create_table(
        "inventory_reservations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("inventory_item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=3), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="ACTIVE", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name="fk_inventory_reservations_organisation_id_organisations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_inventory_reservations_inventory_item_id_inventory_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            name="fk_inventory_reservations_deal_id_deals",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_inventory_reservations_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_reservations"),
    )
    op.create_index(
        "ix_inventory_reservations_organisation_id",
        "inventory_reservations",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_reservations_inventory_item_id",
        "inventory_reservations",
        ["inventory_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_reservations_deal_id",
        "inventory_reservations",
        ["deal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_reservations_deal_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_inventory_item_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_organisation_id", table_name="inventory_reservations")
    op.drop_table("inventory_reservations")

    op.drop_index("ix_inventory_transactions_inventory_item_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_organisation_id", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")

    op.drop_index("ix_inventory_items_sku", table_name="inventory_items")
    op.drop_index("ix_inventory_items_product_id", table_name="inventory_items")
    op.drop_index("ix_inventory_items_organisation_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index("ix_deal_line_items_product_id", table_name="deal_line_items")
    op.drop_index("ix_deal_line_items_deal_id", table_name="deal_line_items")
    op.drop_index("ix_deal_line_items_organisation_id", table_name="deal_line_items")
    op.drop_table("deal_line_items")

    op.drop_index("ix_deals_reference", table_name="deals")
    op.drop_index("ix_deals_organisation_id", table_name="deals")
    op.drop_table("deals")

    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_organisation_id", table_name="products")
    op.drop_table("products")
