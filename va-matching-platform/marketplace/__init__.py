"""
VA Matching Platform - Marketplace Core
========================================
Two-sided marketplace for VA matching built on marketplace-saas patterns.

exports:
- Base: VAProfile, ClientProfile, Match, VASkill, VAStatus, MatchStatus, ClientStatus
- Adapters: Upwork/Fiverr/Toptal/Direct + registry
- Matching: DefaultMatchingAlgorithm, MatchingService, SkillBasedMatcher
- Vetting: VettingService, DefaultVettingWorkflow
- SOPs: SOPTemplate, SOPManager, DEFAULT_SOPS
- Banking: MarketLedger (canonical SalesLedger adapter)
- Payments: PaymentService (canonical Stripe + WebhookGate + ledger)
- Tasks: PlatformTaskManager (canonical async jobs)
"""

from .base import (
    VAProfile,
    ClientProfile,
    Match,
    VASkill,
    VAStatus,
    MatchStatus,
    ClientStatus,
    VASourceAdapter,
    MatchingAlgorithm,
    VettingWorkflow,
    SOPTemplate,
    SOPManager,
)

from .adapters import (
    UpworkAdapter,
    FiverrAdapter,
    ToptalAdapter,
    DirectAdapter,
    VAAdapterRegistry,
    default_registry,
)

from .matching import (
    DefaultMatchingAlgorithm,
    MatchingService,
    SkillBasedMatcher,
    MatchWeights,
)

from .vetting import (
    VettingService,
    DefaultVettingWorkflow,
    VettingWorkflow,
    EnglishTestBank,
    TrialTaskBank,
    DEFAULT_SOPS,
)

from .banking import MarketLedger, get_market_ledger

from .carriers import (
    OnboardingManager,
    DeliveryTracker,
    OnboardingTask,
    OnboardingPlan as SOPOnboardingPlan,
    OnboardingStage,
    MatchStage,
    DeliveryTracking,
)

from .payments import PaymentService, MarketFeeResult, PaymentType as PaymentKind

from .tasks import PlatformTaskManager, get_task_manager

from .notifications import NotificationService

from .storage import DocumentStorage, get_document_storage

__version__ = "2026.10"

__all__ = [
    # Base
    "VAProfile",
    "ClientProfile",
    "Match",
    "VASkill",
    "VAStatus",
    "MatchStatus",
    "ClientStatus",
    "VASourceAdapter",
    "MatchingAlgorithm",
    "VettingWorkflow",
    "SOPTemplate",
    "SOPManager",
    # Adapters
    "UpworkAdapter",
    "FiverrAdapter",
    "ToptalAdapter",
    "DirectAdapter",
    "VAAdapterRegistry",
    "default_registry",
    # Matching
    "DefaultMatchingAlgorithm",
    "MatchingService",
    "SkillBasedMatcher",
    "MatchWeights",
    # Vetting
    "VettingService",
    "DefaultVettingWorkflow",
    "VettingWorkflow",
    "EnglishTestBank",
    "TrialTaskBank",
    "DEFAULT_SOPS",
    # Banking (canonical ledger adapter)
    "MarketLedger",
    "get_market_ledger",
    # Carriers
    "OnboardingManager",
    "DeliveryTracker",
    "OnboardingTask",
    "SOPOnboardingPlan",
    "OnboardingStage",
    "MatchStage",
    "DeliveryTracking",
    # Payments (canonical rails)
    "PaymentService",
    "MarketFeeResult",
    "PaymentKind",
    # Tasks / notifications / storage
    "PlatformTaskManager",
    "get_task_manager",
    "NotificationService",
    "DocumentStorage",
    "get_document_storage",
]
