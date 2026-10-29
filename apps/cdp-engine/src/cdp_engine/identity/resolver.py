"""
Identity Resolution Service
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from rapidfuzz import fuzz, process
import structlog

from ..config import get_cdp_settings
from ..models import (
    UnifiedProfile, IdentitySource, IdentityLink, IdentityResolutionRequest,
    IdentityResolutionResult, MatchType, IdentityType
)

logger = structlog.get_logger(__name__)


class IdentityResolver:
    """
    Identity resolution service with deterministic, probabilistic, and fuzzy matching.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_cdp_settings()
        self._identity_index: Dict[str, Dict[str, uuid.UUID]] = defaultdict(dict)
        self._profile_cache: Dict[uuid.UUID, Any] = {}
        self._fuzzy_cache: Dict[str, List[Tuple[float, uuid.UUID]]] = {}

    async def resolve(self, request: IdentityResolutionRequest) -> IdentityResolutionResult:
        """Resolve identities to a unified profile."""
        start_time = datetime.utcnow()

        # Determine match types to use
        match_types = request.match_types or [
            MatchType.DETERMINISTIC,
            MatchType.PROBABILISTIC,
            MatchType.FUZZY,
        ]

        # Filter by minimum confidence
        min_confidence = request.min_confidence

        # Try deterministic matching first
        resolved_profile = None
        candidates = []
        links = []
        match_type = MatchType.DETERMINISTIC
        confidence = 0.0

        if MatchType.DETERMINISTIC in match_types:
            resolved_profile, det_links, det_confidence = await self._deterministic_match(request.identities)
            if resolved_profile:
                match_type = MatchType.DETERMINISTIC
                confidence = det_confidence
                links.extend(det_links)
                candidates = [resolved_profile]

        # Try probabilistic matching
        if not resolved_profile and MatchType.PROBABILISTIC in match_types:
            resolved_profile, prob_links, prob_confidence = await self._probabilistic_match(request.identities)
            if resolved_profile:
                match_type = MatchType.PROBABILISTIC
                confidence = prob_confidence
                links.extend(prob_links)
                candidates = [resolved_profile]

        # Try fuzzy matching
        if not resolved_profile and MatchType.FUZZY in match_types:
            resolved_profile, fuzzy_links, fuzzy_confidence = await self._fuzzy_match(request.identities)
            if resolved_profile:
                match_type = MatchType.FUZZY
                confidence = fuzzy_confidence
                links.extend(fuzzy_links)
                candidates = [resolved_profile]

        # If still no match, return candidates for review
        if not resolved_profile:
            candidates = await self._find_candidates(request.identities, request.max_candidates)
            confidence = max((c.confidence for c in candidates), default=0.0)
            match_type = MatchType.COMPOSITE

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return IdentityResolutionResult(
            input_identities=request.identities,
            resolved_profile=resolved_profile,
            candidates=candidates[:request.max_candidates],
            links=links,
            confidence=confidence,
            match_type=match_type,
            processing_time_ms=processing_time,
        )

    async def _deterministic_match(
        self, identities: List[Any]
    ) -> Tuple[Optional[Any], List[Any], float]:
        """Deterministic matching based on exact identifier matches."""
        # This would query the database for exact matches
        # For now, return None to indicate no match found
        return None, [], 0.0

    async def _probabilistic_match(
        self, identities: List[Any]
    ) -> Tuple[Optional[Any], List[Any], float]:
        """Probabilistic matching using weighted signals."""
        # This would use ML models to predict match probability
        # For now, return None
        return None, [], 0.0

    async def _fuzzy_match(
        self, identities: List[Any]
    ) -> Tuple[Optional[Any], List[Any], float]:
        """Fuzzy matching using string similarity."""
        # This would use fuzzy string matching
        # For now, return None
        return None, [], 0.0

    async def _find_candidates(
        self, identities: List[Any], max_candidates: int
    ) -> List[Any]:
        """Find candidate profiles for manual review."""
        return []

    async def link_identities(
        self,
        source: Any,
        target: Any,
        match_type: Any,
        confidence: float,
        evidence: Dict[str, Any]
    ) -> Any:
        """Create a link between two identities."""
        link = IdentityLink(
            source_identity=source,
            target_identity=target,
            match_type=match_type,
            confidence=confidence,
            matched_by="system",
            evidence=evidence,
        )
        return link

    async def merge_profiles(
        self,
        source_profile_id: uuid.UUID,
        target_profile_id: uuid.UUID,
        strategy: str = "merge_attributes"
    ) -> Any:
        """Merge two profiles."""
        pass

    async def split_profile(
        self,
        profile_id: uuid.UUID,
        identities_to_move: List[Any],
        new_profile_attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Any]:
        """Split a profile into two."""
        return None, None


class IdentityIndex:
    """In-memory index for fast identity lookups."""

    def __init__(self):
        self._email_index: Dict[str, uuid.UUID] = {}
        self._phone_index: Dict[str, uuid.UUID] = {}
        self._user_id_index: Dict[str, uuid.UUID] = {}
        self._anonymous_id_index: Dict[str, uuid.UUID] = {}
        self._external_id_index: Dict[str, Dict[str, uuid.UUID]] = defaultdict(dict)
        self._device_id_index: Dict[str, uuid.UUID] = {}

    def add(self, profile_id: uuid.UUID, identity: Any) -> None:
        """Add identity to index."""
        if identity.identity_type == "email" and identity.identifier:
            self._email_index[identity.identifier.lower()] = profile_id
        elif identity.identity_type == "phone" and identity.identifier:
            self._phone_index[identity.identifier] = profile_id
        elif identity.identity_type == "user_id" and identity.identifier:
            self._user_id_index[identity.identifier] = profile_id
        elif identity.identity_type == "anonymous_id" and identity.identifier:
            self._anonymous_id_index[identity.identifier] = profile_id
        elif identity.identity_type == "device_id" and identity.identifier:
            self._device_id_index[identity.identifier] = profile_id
        elif identity.identity_type == "external_id" and identity.identifier and identity.source:
            self._external_id_index[identity.source][identity.identifier] = profile_id

    def remove(self, profile_id: uuid.UUID, identity: Any) -> None:
        """Remove identity from index."""
        if identity.identity_type == "email" and identity.identifier:
            self._email_index.pop(identity.identifier.lower(), None)
        elif identity.identity_type == "phone" and identity.identifier:
            self._phone_index.pop(identity.identifier, None)
        elif identity.identity_type == "user_id" and identity.identifier:
            self._user_id_index.pop(identity.identifier, None)
        elif identity.identity_type == "anonymous_id" and identity.identifier:
            self._anonymous_id_index.pop(identity.identifier, None)
        elif identity.identity_type == "device_id" and identity.identifier:
            self._device_id_index.pop(identity.identifier, None)
        elif identity.identity_type == "external_id" and identity.identifier and identity.source:
            self._external_id_index[identity.source].pop(identity.identifier, None)

    def lookup(self, identity: Any) -> Optional[uuid.UUID]:
        """Lookup profile ID by identity."""
        if identity.identity_type == "email" and identity.identifier:
            return self._email_index.get(identity.identifier.lower())
        elif identity.identity_type == "phone" and identity.identifier:
            return self._phone_index.get(identity.identifier)
        elif identity.identity_type == "user_id" and identity.identifier:
            return self._user_id_index.get(identity.identifier)
        elif identity.identity_type == "anonymous_id" and identity.identifier:
            return self._anonymous_id_index.get(identity.identifier)
        elif identity.identity_type == "device_id" and identity.identifier:
            return self._device_id_index.get(identity.identifier)
        elif identity.identity_type == "external_id" and identity.identifier and identity.source:
            return self._external_id_index.get(identity.source, {}).get(identity.identifier)
        return None

    def get_all_for_profile(self, profile_id: uuid.UUID) -> List[str]:
        """Get all indexed identifiers for a profile."""
        # This would need a reverse index in production
        return []


class FuzzyMatcher:
    """Fuzzy string matching for identity resolution."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def match_email(self, email1: str, email2: str) -> float:
        """Compare two emails with fuzzy matching."""
        if not email1 or not email2:
            return 0.0

        # Normalize emails
        e1 = email1.lower().strip()
        e2 = email2.lower().strip()

        if e1 == e2:
            return 1.0

        # Compare local parts and domains separately
        try:
            local1, domain1 = e1.split("@", 1)
            local2, domain2 = e2.split("@", 1)

            domain_score = fuzz.ratio(domain1, domain2) / 100.0
            local_score = fuzz.ratio(local1, local2) / 100.0

            # Weight domain higher (typos more likely in local part)
            return domain_score * 0.7 + local_score * 0.3
        except ValueError:
            return fuzz.ratio(e1, e2) / 100.0

    def match_name(self, name1: str, name2: str) -> float:
        """Compare two names with fuzzy matching."""
        if not name1 or not name2:
            return 0.0

        return fuzz.ratio(name1.lower(), name2.lower()) / 100.0

    def match_phone(self, phone1: str, phone2: str) -> float:
        """Compare two phone numbers."""
        if not phone1 or not phone2:
            return 0.0

        # Normalize phones (remove non-digits)
        import re
        p1 = re.sub(r"\D", "", phone1)
        p2 = re.sub(r"\D", "", phone2)

        if p1 == p2:
            return 1.0

        # Check if one is substring of another (different formats)
        if p1 in p2 or p2 in p1:
            return 0.9

        return fuzz.ratio(p1, p2) / 100.0

    def match_address(self, addr1: str, addr2: str) -> float:
        """Compare two addresses."""
        if not addr1 or not addr2:
            return 0.0

        return fuzz.token_set_ratio(addr1.lower(), addr2.lower()) / 100.0