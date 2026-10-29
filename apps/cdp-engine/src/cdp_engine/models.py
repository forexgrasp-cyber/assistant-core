"""
CDP Engine Models
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class IdentityType(str, Enum):
    """Types of identity"""
    USER_ID = "user_id"
    EMAIL = "email"
    PHONE = "phone"
    ANONYMOUS_ID = "anonymous_id"
    EXTERNAL_ID = "external_id"
    DEVICE_ID = "device_id"
    COOKIE_ID = "cookie_id"


class MatchType(str, Enum):
    """Identity match types"""
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"
    FUZZY = "fuzzy"
    COMPOSITE = "composite"


class IdentitySource(BaseModel):
    """Identity from a specific source"""
    source: str
    identifier: str
    identity_type: IdentityType
    confidence: float = 1.0
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IdentityLink(BaseModel):
    """Link between identities"""
    source_identity: IdentitySource
    target_identity: IdentitySource
    match_type: MatchType
    confidence: float
    matched_at: datetime = Field(default_factory=datetime.utcnow)
    matched_by: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class UnifiedProfile(BaseModel):
    """Unified customer profile"""
    profile_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    identities: List[IdentitySource] = Field(default_factory=list)
    primary_identity: Optional[IdentitySource] = None

    # Profile attributes
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Demographics
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None

    # Attributes
    attributes: Dict[str, Any] = Field(default_factory=dict)
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)

    # Consent & Privacy
    consent_status: Dict[str, bool] = Field(default_factory=dict)
    gdpr_consent: bool = False
    ccpa_opt_out: bool = False
    marketing_opt_in: bool = True

    # Engagement
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None
    session_count: int = 0
    event_count: int = 0
    lifetime_value: float = 0.0

    # Segments
    segment_ids: List[uuid.UUID] = Field(default_factory=list)
    segment_membership: Dict[uuid.UUID, datetime] = Field(default_factory=dict)

    # Predictions
    churn_score: Optional[float] = None
    ltv_prediction: Optional[float] = None
    next_best_action: Optional[str] = None
    propensity_scores: Dict[str, float] = Field(default_factory=dict)

    # Enrichment
    enriched_data: Dict[str, Any] = Field(default_factory=dict)
    enrichment_sources: List[str] = Field(default_factory=list)
    last_enriched: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
        }
    )


class ProfileUpdate(BaseModel):
    """Profile update request"""
    profile_id: uuid.UUID
    attributes: Dict[str, Any] = Field(default_factory=dict)
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)
    identities: Optional[List[IdentitySource]] = None
    consent_updates: Optional[Dict[str, bool]] = None
    version: int


class SegmentRuleOperator(str, Enum):
    """Segment rule operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    REGEX = "regex"
    FUZZY = "fuzzy"


class SegmentRuleLogic(str, Enum):
    """Segment rule logic"""
    AND = "and"
    OR = "or"
    NOT = "not"


class SegmentRule(BaseModel):
    """Individual segment rule"""
    field: str
    operator: SegmentRuleOperator
    value: Any = None
    values: Optional[List[Any]] = None
    logic: SegmentRuleLogic = SegmentRuleLogic.AND
    nested_rules: Optional[List["SegmentRule"]] = None


class SegmentDefinition(BaseModel):
    """Segment definition"""
    segment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    rules: List[SegmentRule] = Field(default_factory=list)
    logic: SegmentRuleLogic = SegmentRuleLogic.AND
    is_dynamic: bool = True
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Segment(BaseModel):
    """Computed segment with members"""
    segment_id: uuid.UUID
    definition: SegmentDefinition
    member_count: int = 0
    member_ids: List[uuid.UUID] = Field(default_factory=list)
    estimated_size: int = 0
    last_computed: Optional[datetime] = None
    computation_time_ms: Optional[int] = None
    status: Literal["computing", "ready", "failed"] = "ready"
    error: Optional[str] = None


class SegmentMembership(BaseModel):
    """Profile segment membership"""
    profile_id: uuid.UUID
    segment_id: uuid.UUID
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    is_active: bool = True


class EnrichmentRequest(BaseModel):
    """Enrichment request"""
    profile_ids: List[uuid.UUID]
    providers: Optional[List[str]] = None
    attributes: Optional[List[str]] = None
    force_refresh: bool = False


class EnrichmentResult(BaseModel):
    """Enrichment result"""
    profile_id: uuid.UUID
    provider: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    enriched_at: datetime = Field(default_factory=datetime.utcnow)


class AudienceExport(BaseModel):
    """Audience export request"""
    segment_id: uuid.UUID
    format: Literal["csv", "json", "parquet"] = "csv"
    fields: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    destination: Optional[str] = None  # s3, gcs, ftp, etc.


class IdentityResolutionRequest(BaseModel):
    """Identity resolution request"""
    identities: List[IdentitySource]
    max_candidates: int = 10
    match_types: Optional[List[MatchType]] = None
    min_confidence: float = 0.5


class IdentityResolutionResult(BaseModel):
    """Identity resolution result"""
    input_identities: List[IdentitySource]
    resolved_profile: Optional[UnifiedProfile] = None
    candidates: List[UnifiedProfile] = Field(default_factory=list)
    links: List[IdentityLink] = Field(default_factory=list)
    confidence: float
    match_type: MatchType
    processing_time_ms: int


class ProfileMergeRequest(BaseModel):
    """Profile merge request"""
    source_profile_id: uuid.UUID
    target_profile_id: uuid.UUID
    merge_strategy: Literal["keep_target", "keep_source", "merge_attributes"] = "merge_attributes"
    preserve_history: bool = True


class ProfileSplitRequest(BaseModel):
    """Profile split request"""
    profile_id: uuid.UUID
    identities_to_move: List[IdentitySource]
    new_profile_attributes: Optional[Dict[str, Any]] = None


class ProfileEvent(BaseModel):
    """Profile event for streaming"""
    event_type: Literal["created", "updated", "merged", "split", "enriched", "deleted"]
    profile_id: uuid.UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changes: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Allow forward references
SegmentRule.model_rebuild()