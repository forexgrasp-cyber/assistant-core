"""Ecommerce vertical pack.

Solves: cart abandonment, post-purchase follow-up, win-back.

Workflows:
- cart-abandonment: cart abandoned → recovery offer → email → SMS
- post-purchase: order placed → thank-you email → review request
"""

from __future__ import annotations

from retention_analytics_core.entities.kernel import EntityField, EntitySchema
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep
from retention_analytics_shared_types import EventType

from retention_analytics_vertical_packs import TENANT_ID, VerticalPack

pack = VerticalPack(
    id="ecommerce",
    name="Ecommerce",
    description="Products, orders, subscriptions, cart recovery",
    schemas=[
        EntitySchema(
            id="product",
            name="Product",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="name", type="string", required=True),
                EntityField(name="price", type="number"),
                EntityField(name="sku", type="string"),
                EntityField(name="inventory", type="number"),
            ],
        ),
        EntitySchema(
            id="order",
            name="Order",
            tenant_id=TENANT_ID,
            fields=[
                EntityField(name="customer_email", type="string", required=True),
                EntityField(name="total", type="number"),
                EntityField(name="status", type="string"),
                EntityField(name="cart_id", type="string"),
            ],
        ),
    ],
    workflows=[
        WorkflowDefinition(
            id="ecommerce.cart-abandonment",
            name="Cart Abandonment Recovery",
            tenant_id=TENANT_ID,
            trigger_event=EventType.ORDER_ABANDONED_CART.value,
            steps=[
                WorkflowStep(
                    id="recover_cart",
                    service="ecommerce.core",
                    action="recover_cart",
                    input={"cart_id": "{{event.cart_id}}", "discount": 0.1},
                ),
                WorkflowStep(
                    id="send_recovery_email",
                    service="email",
                    action="send",
                    input={
                        "to": "{{event.customer_email}}",
                        "subject": "Complete your purchase",
                        "body": "You left items in your cart — here's 10% off.",
                    },
                    depends_on=["recover_cart"],
                ),
                WorkflowStep(
                    id="send_recovery_sms",
                    service="sms",
                    action="send",
                    input={"to": "{{event.customer_phone}}", "body": "Complete your cart — 10% off inside."},
                    depends_on=["recover_cart"],
                ),
            ],
        ),
        WorkflowDefinition(
            id="ecommerce.post-purchase",
            name="Post-Purchase Follow-Up",
            tenant_id=TENANT_ID,
            trigger_event=EventType.ORDER_PLACED.value,
            steps=[
                WorkflowStep(
                    id="send_thank_you_email",
                    service="email",
                    action="send",
                    input={
                        "to": "{{event.customer_email}}",
                        "subject": "Thank you for your order",
                        "body": "Your order is confirmed.",
                    },
                ),
            ],
        ),
    ],
    reports=[
        {"id": "ecommerce.sales-by-channel", "name": "Sales by Channel", "format": "pdf"},
        {"id": "ecommerce.cart-abandonment-rate", "name": "Cart Abandonment Rate", "format": "csv"},
    ],
)

__all__ = ["pack"]
