"""
Database models for retention analytics platform.

Comprehensive models covering:
- Multi-tenancy (Platform -> Agency -> Client -> User)
- Authentication & Authorization (Users, Roles, Permissions, MFA, Passkeys)
- Engagement Services (Email, SMS, Push, Flows, Templates)
- Ecommerce (Products, Orders, Customers, Cart)
- Subscriptions (Plans, Subscriptions, Invoices, Dunning)
- Analytics (Events, Metrics, Attribution, Cohorts, RFM)
- Reporting (Reports, Templates, Schedules, Runs)
- Workflows (Definitions, Executions, Triggers)
- Vertical Packs (Packs, Installations, Marketplace)
- Webhooks (Ingress, Egress, DLQ, Signatures)
- Audit & Compliance (Logs, GDPR, DSAR, Consent)
"""

from .base import Base
from .tenancy import Platform, Agency, Client, ClientUser
from .auth import User, Role, Permission, UserRole, UserPermission, MFADevice, Passkey, Session, ApiKey
from .engagement import (
    EmailTemplate, EmailCampaign, EmailMessage, EmailEvent,
    SMSTemplate, SMSCampaign, SMSMessage,
    PushTemplate, PushCampaign, PushMessage,
    FlowDefinition, FlowExecution, FlowNodeExecution,
    TemplateComponent,
    DeliverabilityConfig, DeliverabilityEvent, SuppressionList,
)
from .ecommerce import (
    Product, ProductVariant, ProductCollection, ProductImage,
    Order, OrderItem, OrderEvent, Cart, CartItem,
    Customer, CustomerAddress, CustomerSegment, CustomerSegmentMember, CustomerEvent,
    Fulfillment, Refund, Location, InventoryLevel,
)
from .subscriptions import (
    SubscriptionPlan, Subscription, SubscriptionItem,
    Invoice, InvoiceItem, PaymentMethod, PaymentEvent,
    DunningConfig, DunningEvent, Coupon, CouponRedemption,
)
from .analytics import (
    Event, EventProperty, DailyMetric, CohortMetric,
    RFMMetric, AttributionTouchpoint, AttributionResult,
    PredictiveMetric, AnomalyEvent,
)
from .reporting import (
    ReportDefinition, ReportTemplate,
    ReportRun, ReportSchedule, ReportExport, ReportVersion,
)
from .workflows import (
    WorkflowDefinition, WorkflowVersion,
    WorkflowExecution, WorkflowNodeExecution, WorkflowTrigger,
)
from .vertical_packs import (
    VerticalPack, PackVersion, PackEntity,
    PackInstallation, PackReview, PackCategory,
)
from .webhooks import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, WebhookSignature,
    WebhookRetry, DeadLetterQueue,
)
from .audit import (
    AuditLog, GDPRRequest, ConsentRecord, DataProcessingAgreement,
    EncryptionKey, KeyRotationLog,
)

__all__ = [
    "Base",
    # Tenancy
    "Platform", "Agency", "Client", "ClientUser",
    # Auth
    "User", "Role", "Permission", "UserRole", "UserPermission",
    "MFADevice", "Passkey", "Session", "ApiKey",
    # Engagement
    "EmailTemplate", "EmailCampaign", "EmailMessage", "EmailEvent",
    "SMSTemplate", "SMSCampaign", "SMSMessage",
    "PushTemplate", "PushCampaign", "PushMessage",
    "FlowDefinition", "FlowExecution", "FlowNodeExecution",
    "TemplateComponent",
    "DeliverabilityConfig", "DeliverabilityEvent", "SuppressionList",
    # Ecommerce
    "Product", "ProductVariant", "ProductCollection", "ProductImage",
    "Order", "OrderItem", "OrderEvent", "Cart", "CartItem",
    "Customer", "CustomerAddress", "CustomerSegment", "CustomerSegmentMember", "CustomerEvent",
    "Fulfillment", "Refund", "Location", "InventoryLevel",
    # Subscriptions
    "SubscriptionPlan", "Subscription", "SubscriptionItem",
    "Invoice", "InvoiceItem", "PaymentMethod", "PaymentEvent",
    "DunningConfig", "DunningEvent", "Coupon", "CouponRedemption",
    # Analytics
    "Event", "EventProperty", "DailyMetric", "CohortMetric",
    "RFMMetric", "AttributionTouchpoint", "AttributionResult",
    "PredictiveMetric", "AnomalyEvent",
    # Reporting
    "ReportDefinition", "ReportTemplate",
    "ReportRun", "ReportSchedule", "ReportExport", "ReportVersion",
    # Workflows
    "WorkflowDefinition", "WorkflowVersion",
    "WorkflowExecution", "WorkflowNodeExecution", "WorkflowTrigger",
    # Vertical Packs
    "VerticalPack", "PackVersion", "PackEntity",
    "PackInstallation", "PackReview", "PackCategory",
    # Webhooks
    "WebhookEndpoint", "WebhookEvent", "WebhookDelivery", "WebhookSignature",
    "WebhookRetry", "DeadLetterQueue",
    # Audit
    "AuditLog", "GDPRRequest", "ConsentRecord", "DataProcessingAgreement",
    "EncryptionKey", "KeyRotationLog",
]