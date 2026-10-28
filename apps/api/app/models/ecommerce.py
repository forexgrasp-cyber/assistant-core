"""
Ecommerce models: Products, Orders, Customers, Cart.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, Enum as SQLEnum, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from .base import SoftDeleteModel


class ProductCollection(SoftDeleteModel):
    """Product collection/category."""
    __tablename__ = "product_collections"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    seo_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seo_keywords: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Relationships
    parent: Mapped[Optional["ProductCollection"]] = relationship("ProductCollection", remote_side="ProductCollection.id", backref="children")
    products: Mapped[List["Product"]] = relationship("Product", back_populates="collection")
    
    __table_args__ = (
        Index("ix_product_collections_client_slug", "client_id", "slug", unique=True),
    )


class Product(SoftDeleteModel):
    """Product."""
    __tablename__ = "products"
    
    collection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    handle: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    cost_per_item: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Inventory
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    inventory_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inventory_policy: Mapped[str] = mapped_column(String(20), default="deny", nullable=False)  # deny, continue
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Variants
    has_variants: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    variant_options: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Images
    images: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    featured_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # SEO
    seo_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seo_keywords: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)  # active, draft, archived
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_shipping: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_digital: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_gift_card: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Vendor/Type
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Weight for shipping
    weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(10), default="g", nullable=False)
    
    # Digital product
    digital_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    digital_download_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    collection: Mapped[Optional["ProductCollection"]] = relationship("ProductCollection", back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")
    
    __table_args__ = (
        Index("ix_products_client_slug", "client_id", "slug", unique=True),
        Index("ix_products_status_featured", "status", "is_featured"),
    )


class ProductVariant(SoftDeleteModel):
    """Product variant."""
    __tablename__ = "product_variants"
    
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Option values
    option_values: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Pricing
    price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    cost_per_item: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Inventory
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    inventory_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inventory_policy: Mapped[str] = mapped_column(String(20), default="deny", nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    # Weight
    weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(10), default="g", nullable=False)
    
    # Images
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="variant")
    
    __table_args__ = (
        Index("ix_product_variants_product_sku", "product_id", "sku", unique=True),
    )


class ProductImage(SoftDeleteModel):
    """Product image."""
    __tablename__ = "product_images"
    
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    __table_args__ = (
        Index("ix_product_images_product_position", "product_id", "position"),
    )


class Customer(SoftDeleteModel):
    """Customer."""
    __tablename__ = "customers"
    
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Marketing
    accepts_marketing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepts_marketing_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marketing_opt_in_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # none, email, sms, both
    marketing_opt_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_opt_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stats
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    average_order_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    last_order_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_order_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # RFM
    rfm_segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    rfm_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rfm_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Predictive
    predicted_ltv: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    churn_probability: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    next_order_predicted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Tags/Properties
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Tax
    tax_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tax_exemptions: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_order_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Relationships
    addresses: Mapped[List["CustomerAddress"]] = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="customer")
    cart: Mapped[Optional["Cart"]] = relationship("Cart", back_populates="customer", uselist=False)
    segments: Mapped[List["CustomerSegment"]] = relationship("CustomerSegment", secondary="customer_segment_members", back_populates="customers")
    events: Mapped[List["CustomerEvent"]] = relationship("CustomerEvent", back_populates="customer", cascade="all, delete-orphan")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="customer")
    
    __table_args__ = (
        Index("ix_customers_client_email", "client_id", "email", unique=True),
    )


class CustomerAddress(SoftDeleteModel):
    """Customer address."""
    __tablename__ = "customer_addresses"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Type
    type: Mapped[str] = mapped_column(String(20), default="shipping", nullable=False)  # shipping, billing
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Details
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address1: Mapped[str] = mapped_column(String(255), nullable=False)
    address2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    province_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO 3166-1 alpha-2
    country_code: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)  # ISO 3166-1 alpha-3
    zip: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Coordinates
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    
    # Validation
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="addresses")
    
    __table_args__ = (
        Index("ix_customer_addresses_customer_default", "customer_id", "is_default", unique=True, postgresql_where="is_default = true"),
    )


class CustomerSegment(SoftDeleteModel):
    """Customer segment."""
    __tablename__ = "customer_segments"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Definition (dynamic)
    definition: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="dynamic", nullable=False)  # dynamic, static, rfm, predictive
    
    # Stats
    customer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_recalculate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    recalculation_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Usage
    used_in_campaigns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_in_flows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    customers: Mapped[List["Customer"]] = relationship("Customer", secondary="customer_segment_members", back_populates="segments")
    
    __table_args__ = (
        Index("ix_customer_segments_client_slug", "client_id", "slug", unique=True),
    )


class CustomerSegmentMember(SoftDeleteModel):
    """Customer segment membership."""
    __tablename__ = "customer_segment_members"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    added_by: Mapped[str] = mapped_column(String(50), default="system", nullable=False)  # system, manual, rule
    
    __table_args__ = (
        Index("ix_customer_segment_members_customer_segment", "customer_id", "segment_id", unique=True),
    )


class CustomerEvent(SoftDeleteModel):
    """Customer event/activity."""
    __tablename__ = "customer_events"
    
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Properties
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Context
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Session
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Attribution
    attribution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="events")
    
    __table_args__ = (
        Index("ix_customer_events_customer_timestamp", "customer_id", "timestamp"),
        Index("ix_customer_events_type_timestamp", "event_type", "timestamp"),
    )


class Cart(SoftDeleteModel):
    """Shopping cart."""
    __tablename__ = "carts"
    
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, abandoned, converted, expired
    
    # Totals
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Abandoned cart
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_sms_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_carts_status_expires", "status", "expires_at"),
    )


class CartItem(SoftDeleteModel):
    """Cart item."""
    __tablename__ = "cart_items"
    
    cart_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Price at time of adding
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Properties snapshot
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    
    __table_args__ = (
        Index("ix_cart_items_cart_product", "cart_id", "product_id"),
    )


class Order(SoftDeleteModel):
    """Order."""
    __tablename__ = "orders"
    
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Order identifiers
    order_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Shopify-style name (#1001)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, confirmed, processing, shipped, delivered, cancelled, refunded, partially_refunded
    financial_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, authorized, paid, partially_paid, refunded, partially_refunded, voided
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="unfulfilled", nullable=False)  # unfulfilled, partial, fulfilled, restocked
    
    # Totals
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_outstanding: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    currency_rate: Mapped[float] = mapped_column(Numeric(10, 6), default=1, nullable=False)
    
    # Line items
    line_items_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Shipping
    shipping_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_addresses.id", ondelete="SET NULL"),
        nullable=True,
    )
    billing_address_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customer_addresses.id", ondelete="SET NULL"),
        nullable=True,
    )
    shipping_method: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Customer info (snapshot)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    customer_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Attribution
    attribution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    referral_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    landing_page: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referring_site: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Tags/Notes
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Meta
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="orders")
    shipping_address: Mapped[Optional["CustomerAddress"]] = relationship("CustomerAddress", foreign_keys=[shipping_address_id])
    billing_address: Mapped[Optional["CustomerAddress"]] = relationship("CustomerAddress", foreign_keys=[billing_address_id])
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    events: Mapped[List["OrderEvent"]] = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")
    fulfillments: Mapped[List["Fulfillment"]] = relationship("Fulfillment", back_populates="order", cascade="all, delete-orphan")
    refunds: Mapped[List["Refund"]] = relationship("Refund", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_orders_client_placed", "client_id", "placed_at"),
        Index("ix_orders_status_financial", "status", "financial_status"),
    )


class OrderItem(SoftDeleteModel):
    """Order line item."""
    __tablename__ = "order_items"
    
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Product snapshot
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Properties snapshot
    variant_options: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Image
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Pricing
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    price_per_unit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Discounts
    discount_allocations: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    total_discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Tax
    tax_lines: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    total_tax: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Fulfillment
    fulfillment_status: Mapped[str] = mapped_column(String(20), default="unfulfilled", nullable=False)
    fulfilled_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Refunds
    refunded_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refunded_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="order_items")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", back_populates="order_items")
    
    __table_args__ = (
        Index("ix_order_items_order", "order_id"),
    )


class OrderEvent(SoftDeleteModel):
    """Order event/activity."""
    __tablename__ = "order_events"
    
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Details
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Actor
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="events")
    user: Mapped[Optional["User"]] = relationship("User")
    
    __table_args__ = (
        Index("ix_order_events_order_timestamp", "order_id", "timestamp"),
    )


class Fulfillment(SoftDeleteModel):
    """Order fulfillment."""
    __tablename__ = "fulfillments"
    
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, open, success, cancelled, failure
    
    # Tracking
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Items
    line_items: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # Location
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Receipt
    receipt: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="fulfillments")
    
    __table_args__ = (
        Index("ix_fulfillments_order", "order_id"),
    )


class Refund(SoftDeleteModel):
    """Order refund."""
    __tablename__ = "refunds"
    
    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Amount
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # Reason
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Items
    line_items: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    restock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, processed, failed, cancelled
    
    # Transaction
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Timestamps
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="refunds")
    
    __table_args__ = (
        Index("ix_refunds_order", "order_id"),
    )


class Location(SoftDeleteModel):
    """Inventory location/warehouse."""
    __tablename__ = "locations"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address1: Mapped[str] = mapped_column(String(255), nullable=False)
    address2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    province_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    zip: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Type
    type: Mapped[str] = mapped_column(String(20), default="warehouse", nullable=False)  # warehouse, retail, dropship
    
    # Capabilities
    fulfills_online_orders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fulfills_local_delivery: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fulfills_pickup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Priority
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    inventory_levels: Mapped[List["InventoryLevel"]] = relationship("InventoryLevel", back_populates="location", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_locations_client_active", "client_id", "is_active"),
    )


class InventoryLevel(SoftDeleteModel):
    """Inventory level at a location."""
    __tablename__ = "inventory_levels"
    
    location_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incoming: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    committed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    location: Mapped["Location"] = relationship("Location", back_populates="inventory_levels")
    
    __table_args__ = (
        Index("ix_inventory_levels_location_product", "location_id", "product_id", unique=True),
        Index("ix_inventory_levels_location_variant", "location_id", "variant_id", unique=True),
    )
