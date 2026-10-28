"""
Ecommerce API endpoints: Products, Orders, Subscriptions.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    Product, ProductVariant, ProductCollection, ProductImage,
    Order, OrderItem, OrderEvent,
    Subscription, SubscriptionPlan, SubscriptionItem,
    Invoice, InvoiceItem, PaymentMethod, PaymentEvent,
    DunningConfig, DunningEvent, Coupon, CouponRedemption,
    Customer, CustomerAddress, Fulfillment, Refund, Location, InventoryLevel
)

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.post("/products", status_code=201)
async def create_product(
    product_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Product
    
    product = Product(
        client_id=current_user.client_id,
        external_id=product_data.get("external_id"),
        name=product_data.get("name"),
        slug=product_data.get("slug") or product_data.get("name", "").lower().replace(" ", "-"),
        description=product_data.get("description"),
        price=product_data.get("price", 0),
        compare_at_price=product_data.get("compare_at_price"),
        cost_per_item=product_data.get("cost_per_item"),
        track_inventory=product_data.get("track_inventory", True),
        inventory_quantity=product_data.get("inventory_quantity", 0),
        vendor=product_data.get("vendor"),
        product_type=product_data.get("product_type"),
        tags=product_data.get("tags", []),
        images=product_data.get("images", []),
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"id": str(product.id), "message": "Product created"}

@router.get("/products")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    collection_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Product
    from sqlalchemy import desc
    
    query = select(Product).where(Product.client_id == current_user.client_id)
    
    if status:
        query = query.where(Product.status == status)
    if collection_id:
        query = query.where(Product.collection_id == collection_id)
    
    query = query.order_by(desc(Product.created_at))
    
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Product.id).where(Product.client_id == current_user.client_id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()
    
    return {
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "price": float(p.price),
                "status": p.status,
                "inventory_quantity": p.inventory_quantity,
            }
            for p in products
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/products/{product_id}/variants", status_code=201)
async def create_variant(
    product_id: str,
    variant_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Product, ProductVariant
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.client_id == current_user.client_id
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    variant = ProductVariant(
        product_id=product.id,
        sku=variant_data.get("sku"),
        option_values=variant_data.get("option_values", {}),
        price=variant_data.get("price"),
        inventory_quantity=variant_data.get("inventory_quantity", 0),
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return {"id": str(variant.id), "message": "Variant created"}

@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import desc
    
    query = select(Order).where(Order.client_id == current_user.client_id)
    
    if status:
        query = query.where(Order.status == status)
    if customer_id:
        query = query.where(Order.customer_id == customer_id)
    
    query = query.order_by(desc(Order.placed_at))
    
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Order.id).where(Order.client_id == current_user.client_id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return {
        "orders": [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "customer_id": str(o.customer_id) if o.customer_id else None,
                "total": float(o.total),
                "status": o.status,
                "financial_status": o.financial_status,
                "fulfillment_status": o.fulfillment_status,
                "placed_at": o.placed_at.isoformat(),
            }
            for o in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Order, OrderItem
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.client_id == current_user.client_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "customer_id": str(order.customer_id) if order.customer_id else None,
        "total": float(order.total),
        "status": order.status,
        "financial_status": order.financial_status,
        "fulfillment_status": order.fulfillment_status,
        "placed_at": order.placed_at.isoformat(),
        "line_items": [
            {
                "id": str(item.id),
                "product_title": item.product_title,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
            }
            for item in order.items
        ],
    }

@router.post("/subscriptions/plans", status_code=201)
async def create_subscription_plan(
    plan_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import SubscriptionPlan
    
    plan = SubscriptionPlan(
        client_id=current_user.client_id,
        name=plan_data.get("name"),
        price=plan_data.get("price"),
        interval=plan_data.get("interval"),
        interval_count=plan_data.get("interval_count", 1),
        trial_days=plan_data.get("trial_days", 0),
        features=plan_data.get("features", []),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return {"id": str(plan.id), "message": "Plan created"}

@router.get("/subscriptions/plans")
async def list_plans(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import SubscriptionPlan
    result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.client_id == current_user.client_id,
            SubscriptionPlan.status == "active"
        ).order_by(SubscriptionPlan.price)
    )
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "price": float(p.price),
            "interval": p.interval,
            "interval_count": p.interval_count,
            "trial_days": p.trial_days,
        }
        for p in plans
    ]

@router.post("/subscriptions", status_code=201)
async def create_subscription(
    subscription_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Subscription, SubscriptionPlan, Customer
    
    result = await db.execute(
        select(Customer).where(
            Customer.id == subscription_data.get("customer_id"),
            Customer.client_id == current_user.client_id
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    plan_result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == subscription_data.get("plan_id"))
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    subscription = Subscription(
        customer_id=customer.id,
        plan_id=plan.id,
        payment_method_id=subscription_data.get("payment_method_id"),
        quantity=subscription_data.get("quantity", 1),
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return {"id": str(subscription.id), "message": "Subscription created"}

@router.get("/subscriptions")
async def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Subscription
    from sqlalchemy import desc
    
    query = select(Subscription).where(Subscription.client_id == current_user.client_id)
    
    if status:
        query = query.where(Subscription.status == status)
    
    query = query.order_by(desc(Subscription.created_at))
    
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Subscription.id).where(Subscription.client_id == current_user.client_id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return {
        "subscriptions": [
            {
                "id": str(s.id),
                "customer_id": str(s.customer_id),
                "plan_id": str(s.plan_id),
                "status": s.status,
                "current_period_end": s.current_period_end.isoformat(),
            }
            for s in subscriptions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    reason: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.client_id == current_user.client_id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    subscription.status = "cancelled"
    subscription.cancelled_at = datetime.utcnow()
    subscription.cancellation_reason = reason
    await db.commit()
    return {"message": "Subscription cancelled"}

@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Invoice
    from sqlalchemy import desc
    
    query = select(Invoice).where(Invoice.client_id == current_user.client_id)
    
    if status:
        query = query.where(Invoice.status == status)
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
    
    query = query.order_by(desc(Invoice.issued_at))
    
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Invoice.id).where(Invoice.client_id == current_user.client_id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return {
        "invoices": [
            {
                "id": str(i.id),
                "invoice_number": i.invoice_number,
                "customer_id": str(i.customer_id),
                "status": i.status,
                "total": float(i.total),
                "due_at": i.due_at.isoformat() if i.due_at else None,
            }
            for i in invoices
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/invoices/{invoice_id}/pay")
async def pay_invoice(
    invoice_id: str,
    payment_method_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Payment initiated"}

@router.post("/coupons", status_code=201)
async def create_coupon(
    coupon_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Coupon
    
    coupon = Coupon(
        client_id=current_user.client_id,
        code=coupon_data.get("code"),
        name=coupon_data.get("name"),
        type=coupon_data.get("type", "percentage"),
        value=coupon_data.get("value"),
        max_redemptions=coupon_data.get("max_redemptions"),
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return {"id": str(coupon.id), "message": "Coupon created"}

@router.get("/coupons")
async def list_coupons(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Coupon
    result = await db.execute(
        select(Coupon).where(Coupon.client_id == current_user.client_id).order_by(Coupon.created_at.desc())
    )
    coupons = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "type": c.type,
            "value": float(c.value),
            "is_active": c.is_active,
        }
        for c in coupons
    ]