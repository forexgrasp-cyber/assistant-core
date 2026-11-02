"""
Base Classes for VA Marketplace
==============================
Abstract base classes for VA source adapters, matching, and marketplace operations.
"""

from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class VAStatus(str, Enum):
    """VA lifecycle status."""
    PENDING = "pending"
    VETTING = "vetting"
    ACTIVE = "active"
    MATCHED = "matched"
    INACTIVE = "inactive"
    REJECTED = "rejected"


class MatchStatus(str, Enum):
    """Match lifecycle status."""
    PROPOSED = "proposed"
    INTRO_SENT = "intro_sent"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class ClientStatus(str, Enum):
    """Client lifecycle status."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    CHURNED = "churned"


@dataclass
class VASkill:
    """VA skill with proficiency level."""
    name: str
    category: str
    proficiency: int  # 1-5
    years_experience: float = 0.0
    certifications: list[str] = field(default_factory=list)


@dataclass
class VAProfile:
    """Complete VA profile."""
    id: str = field(default_factory=lambda: str(uuid4()))
    email: str = ""
    full_name: str = ""
    timezone: str = "UTC"
    hourly_rate: float = 0.0
    availability_hours_per_week: int = 0
    skills: list[VASkill] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["English"])
    location: str = ""
    bio: str = ""
    portfolio_url: str = ""
    linkedin_url: str = ""
    status: VAStatus = VAStatus.PENDING
    source: str = ""  # upwork, fiverr, toptal, direct
    source_profile_url: str = ""
    source_rating: float = 0.0
    source_reviews_count: int = 0
    vetting_score: float = 0.0
    english_test_score: float = 0.0
    trial_task_score: float = 0.0
    reference_check_passed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "timezone": self.timezone,
            "hourly_rate": self.hourly_rate,
            "availability_hours_per_week": self.availability_hours_per_week,
            "skills": [{"name": s.name, "category": s.category, "proficiency": s.proficiency,
                        "years_experience": s.years_experience, "certifications": s.certifications}
                       for s in self.skills],
            "languages": self.languages,
            "location": self.location,
            "bio": self.bio,
            "portfolio_url": self.portfolio_url,
            "linkedin_url": self.linkedin_url,
            "status": self.status.value,
            "source": self.source,
            "source_profile_url": self.source_profile_url,
            "source_rating": self.source_rating,
            "source_reviews_count": self.source_reviews_count,
            "vetting_score": self.vetting_score,
            "english_test_score": self.english_test_score,
            "trial_task_score": self.trial_task_score,
            "reference_check_passed": self.reference_check_passed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ClientProfile:
    """Client profile with needs."""
    id: str = field(default_factory=lambda: str(uuid4()))
    email: str = ""
    company_name: str = ""
    contact_name: str = ""
    timezone: str = "UTC"
    industry: str = ""
    company_size: int = 0
    monthly_budget: Decimal = Decimal("0.0")
    needed_hours_per_week: int = 0
    required_skills: list[str] = field(default_factory=list)
    preferred_timezone_overlap_hours: int = 4
    max_hourly_rate: Decimal = Decimal("0.0")
    tasks_to_delegate: list[str] = field(default_factory=list)
    current_tools: list[str] = field(default_factory=list)
    status: ClientStatus = ClientStatus.LEAD
    source: str = "direct"
    assigned_va_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "timezone": self.timezone,
            "industry": self.industry,
            "company_size": self.company_size,
            "monthly_budget": self.monthly_budget,
            "needed_hours_per_week": self.needed_hours_per_week,
            "required_skills": self.required_skills,
            "preferred_timezone_overlap_hours": self.preferred_timezone_overlap_hours,
            "max_hourly_rate": self.max_hourly_rate,
            "tasks_to_delegate": self.tasks_to_delegate,
            "current_tools": self.current_tools,
            "status": self.status.value,
            "source": self.source,
            "assigned_va_id": self.assigned_va_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Match:
    """Match between client and VA."""
    id: str = field(default_factory=lambda: str(uuid4()))
    client_id: str = ""
    va_id: str = ""
    status: MatchStatus = MatchStatus.PROPOSED
    match_score: float = 0.0
    match_factors: dict = field(default_factory=dict)
    proposed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    intro_sent_at: datetime | None = None
    interview_scheduled_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str = ""
    onboarding_started_at: datetime | None = None
    onboarding_completed_at: datetime | None = None
    placement_fee_charged: bool = False
    platform_fee_charged: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "va_id": self.va_id,
            "status": self.status.value,
            "match_score": self.match_score,
            "match_factors": self.match_factors,
            "proposed_at": self.proposed_at.isoformat(),
            "intro_sent_at": self.intro_sent_at.isoformat() if self.intro_sent_at else None,
            "interview_scheduled_at": self.interview_scheduled_at.isoformat() if self.interview_scheduled_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "onboarding_started_at": self.onboarding_started_at.isoformat() if self.onboarding_started_at else None,
            "onboarding_completed_at": self.onboarding_completed_at.isoformat() if self.onboarding_completed_at else None,
            "placement_fee_charged": self.placement_fee_charged,
            "platform_fee_charged": self.platform_fee_charged,
            "metadata": self.metadata,
        }


class VASourceAdapter(abc.ABC):
    """Abstract base for VA source adapters (Upwork, Fiverr, Toptal, Direct)."""

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Source identifier (e.g., 'upwork', 'fiverr')."""
        pass

    @abc.abstractmethod
    async def search_vas(
        self,
        skills: list[str],
        min_hourly_rate: float | None = None,
        max_hourly_rate: float | None = None,
        min_rating: float | None = None,
        timezone: str | None = None,
        availability_hours: int | None = None,
        limit: int = 50,
    ) -> list[VAProfile]:
        """Search for VAs matching criteria."""
        pass

    @abc.abstractmethod
    async def get_va_details(self, va_id: str) -> VAProfile | None:
        """Get detailed VA profile by ID."""
        pass

    @abc.abstractmethod
    async def get_va_reviews(self, va_id: str) -> list[dict]:
        """Get VA reviews."""
        pass

    @abc.abstractmethod
    async def invite_va(self, va_id: str, message: str) -> bool:
        """Invite VA to platform."""
        pass


class MatchingAlgorithm(abc.ABC):
    """Abstract base for matching algorithms."""

    @abc.abstractmethod
    async def find_matches(
        self,
        client: ClientProfile,
        va_pool: list[VAProfile],
        limit: int = 5,
    ) -> list[Match]:
        """Find best VA matches for client."""
        pass

    @abc.abstractmethod
    def calculate_match_score(self, client: ClientProfile, va: VAProfile) -> tuple[float, dict]:
        """Calculate match score and factors."""
        pass


class VettingWorkflow(abc.ABC):
    """Abstract base for VA vetting workflow."""

    @abc.abstractmethod
    async def run_english_test(self, va_id: str, test_type: str = "standard") -> float:
        """Run English proficiency test."""
        pass

    @abc.abstractmethod
    async def run_trial_task(self, va_id: str, task_id: str) -> float:
        """Run trial task assessment."""
        pass

    @abc.abstractmethod
    async def check_references(self, va_id: str, references: list[dict]) -> bool:
        """Check VA references."""
        pass

    @abc.abstractmethod
    async def calculate_vetting_score(self, va_id: str) -> float:
        """Calculate overall vetting score."""
        pass


@dataclass
class SOPTemplate:
    """Standard Operating Procedure template."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""  # onboarding, communication, task_management, reporting
    content: str = ""  # Markdown content with placeholders
    variables: list[str] = field(default_factory=list)  # {{client_name}}, {{va_name}}, etc.
    version: int = 1
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def render(self, variables: dict) -> str:
        """Render template with variables."""
        content = self.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content


class SOPManager:
    """Manages SOP templates and generation."""

    def __init__(self):
        self.templates: dict[str, SOPTemplate] = {}

    def add_template(self, template: SOPTemplate):
        self.templates[template.id] = template

    def get_template(self, template_id: str) -> SOPTemplate | None:
        return self.templates.get(template_id)

    def list_templates(self, category: str | None = None) -> list[SOPTemplate]:
        if category:
            return [t for t in self.templates.values() if t.category == category and t.is_active]
        return [t for t in self.templates.values() if t.is_active]

    def generate_sop(self, template_id: str, variables: dict) -> str | None:
        template = self.get_template(template_id)
        if not template:
            return None
        return template.render(variables)