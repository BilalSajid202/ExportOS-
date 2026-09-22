"""
Tradeloop — Product Catalogue API Routes

Endpoints:
  POST   /products
  GET    /products
  GET    /products/{product_id}
  PUT    /products/{product_id}
  DELETE /products/{product_id}
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.product import ProductCreateRequest, ProductResponse, ProductUpdateRequest

router = APIRouter(prefix="/products", tags=["Products"])

_CATALOGUE_ROLES = require_roles(
    UserRole.ADMIN,
    UserRole.EXPORT_MANAGER,
    UserRole.SALES,
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    payload: ProductCreateRequest,
    current_user: User = Depends(_CATALOGUE_ROLES),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    sku = payload.sku.strip().upper()
    existing = await db.execute(
        select(Product).where(
            Product.organisation_id == current_user.organisation_id,
            Product.sku == sku,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SKU '{sku}' already exists in this organisation",
        )

    product = Product(
        organisation_id=current_user.organisation_id,
        sku=sku,
        name=payload.name.strip(),
        description=payload.description,
        unit_of_measure=payload.unit_of_measure.upper(),
        selling_currency=payload.selling_currency.upper(),
        default_hs_code=payload.default_hs_code,
        weight_kg=payload.weight_kg,
        carton_capacity=payload.carton_capacity,
        base_cost=payload.base_cost,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List products (optional search)",
)
async def list_products(
    q: Optional[str] = Query(None, description="Search by SKU or name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProductResponse]:
    query = select(Product).where(
        Product.organisation_id == current_user.organisation_id
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(
            or_(Product.sku.ilike(term), Product.name.ilike(term))
        )
    query = query.order_by(Product.name.asc())
    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductResponse.model_validate(p) for p in products]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
)
async def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await _get_tenant_product(db, current_user.organisation_id, product_id)
    return ProductResponse.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    current_user: User = Depends(_CATALOGUE_ROLES),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    product = await _get_tenant_product(db, current_user.organisation_id, product_id)

    if payload.sku is not None:
        new_sku = payload.sku.strip().upper()
        if new_sku != product.sku:
            clash = await db.execute(
                select(Product).where(
                    Product.organisation_id == current_user.organisation_id,
                    Product.sku == new_sku,
                    Product.id != product.id,
                )
            )
            if clash.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SKU '{new_sku}' already exists in this organisation",
                )
            product.sku = new_sku

    if payload.name is not None:
        product.name = payload.name.strip()
    if payload.description is not None:
        product.description = payload.description
    if payload.unit_of_measure is not None:
        product.unit_of_measure = payload.unit_of_measure.upper()
    if payload.selling_currency is not None:
        product.selling_currency = payload.selling_currency.upper()
    if payload.default_hs_code is not None:
        product.default_hs_code = payload.default_hs_code
    if payload.weight_kg is not None:
        product.weight_kg = payload.weight_kg
    if payload.carton_capacity is not None:
        product.carton_capacity = payload.carton_capacity
    if payload.base_cost is not None:
        product.base_cost = payload.base_cost

    await db.commit()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product(
    product_id: UUID,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EXPORT_MANAGER)
    ),
    db: AsyncSession = Depends(get_db),
) -> None:
    product = await _get_tenant_product(db, current_user.organisation_id, product_id)
    await db.delete(product)
    await db.commit()


async def _get_tenant_product(
    db: AsyncSession,
    organisation_id: UUID,
    product_id: UUID,
) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.organisation_id == organisation_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product
