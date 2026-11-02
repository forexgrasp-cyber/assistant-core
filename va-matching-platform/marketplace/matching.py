"""
Matching Algorithm
==================
Advanced VA-client matching with multi-factor scoring.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .base import ClientProfile, Match, MatchStatus, MatchingAlgorithm, VAProfile, VAStatus

log = logging.getLogger(__name__)


@dataclass
class MatchWeights:
    """Weights for match scoring factors."""
    skill_match: float = 0.30
    rate_fit: float = 0.20
    availability_fit: float = 0.15
    timezone_overlap: float = 0.15
    vetting_score: float = 0.10
    source_rating: float = 0.10


class DefaultMatchingAlgorithm:
    """Default matching algorithm with weighted multi-factor scoring."""

    def __init__(self, weights: MatchWeights | None = None):
        self.weights = weights or MatchWeights()

    async def find_matches(
        self,
        client,
        va_pool: list,
        limit: int = 5,
    ) -> list:
        """Find best VA matches for client."""
        if not va_pool:
            return []

        # Filter to active, vetted VAs
        eligible_vas = [
            va for va in va_pool
            if va.status == "active" and va.vetting_score >= 0.6
        ]

        if not eligible_vas:
            log.warning("No eligible VAs in pool")
            return []

        # Calculate scores
        matches = []
        for va in eligible_vas:
            score, factors = self.calculate_match_score(client, va)
            match = Match(
                client_id=client.id,
                va_id=va.id,
                status=MatchStatus.PROPOSED,
                match_score=score,
                match_factors=factors,
            )
            matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:limit]

    def calculate_match_score(self, client, va) -> tuple[float, dict]:
        """Calculate match score and factors."""
        factors = {}

        # 1. Skill match (0-1)
        skill_score = self._calculate_skill_match(client, va)
        factors["skill_match"] = skill_score

        # 2. Rate fit (0-1)
        rate_score = self._calculate_rate_fit(client, va)
        factors["rate_fit"] = rate_score

        # 3. Availability fit (0-1)
        avail_score = self._calculate_availability_fit(client, va)
        factors["availability_fit"] = avail_score

        # 4. Timezone overlap (0-1)
        tz_score = self._calculate_timezone_overlap(client, va)
        factors["timezone_overlap"] = tz_score

        # 5. Vetting score (0-1)
        vetting_score = va.vetting_score
        factors["vetting_score"] = vetting_score

        # 6. Source rating (0-1, normalized)
        source_score = min(va.source_rating / 5.0, 1.0)
        factors["source_rating"] = source_score

        # Weighted total
        w = self.weights
        total = (
            w.skill_match * skill_score +
            w.rate_fit * rate_score +
            w.availability_fit * avail_score +
            w.timezone_overlap * tz_score +
            w.vetting_score * vetting_score +
            w.source_rating * source_score
        )

        # Normalize to 0-1
        total = max(0.0, min(1.0, total))

        return total, factors

    def _calculate_skill_match(self, client, va) -> float:
        """Calculate skill overlap score."""
        if not client.required_skills:
            return 0.5  # Neutral if no requirements

        client_skills = set(s.lower().strip() for s in client.required_skills)
        va_skills = set(s.name.lower().strip() for s in va.skills)

        if not va_skills:
            return 0.0

        # Jaccard similarity
        intersection = client_skills & va_skills
        union = client_skills | va_skills
        return len(intersection) / len(union) if union else 0.0

    def _calculate_rate_fit(self, client, va) -> float:
        """Calculate rate compatibility."""
        if client.max_hourly_rate <= 0:
            return 0.5  # Neutral if no budget specified

        if va.hourly_rate <= client.max_hourly_rate:
            # Within budget - higher score for better value
            ratio = va.hourly_rate / client.max_hourly_rate
            return 1.0 - (ratio * 0.3)  # Slightly penalize expensive
        else:
            # Over budget - penalize
            overage = (va.hourly_rate - client.max_hourly_rate) / client.max_hourly_rate
            return max(0.0, 0.5 - overage)

    def _calculate_availability_fit(self, client, va) -> float:
        """Calculate availability fit."""
        if client.needed_hours_per_week <= 0:
            return 0.5

        if va.availability_hours_per_week >= client.needed_hours_per_week:
            return 1.0
        else:
            return va.availability_hours_per_week / client.needed_hours_per_week

    def _calculate_timezone_overlap(self, client, va) -> float:
        """Calculate timezone overlap score."""
        try:
            # Simple timezone overlap calculation
            # In production, use proper timezone library (pytz/zoneinfo)
            client_tz = client.timezone
            va_tz = va.timezone

            if client_tz == va_tz:
                return 1.0

            # Rough overlap calculation based on region
            client_region = self._get_region(client_tz)
            va_region = self._get_region(va_tz)

            if client_region == va_region:
                return 0.8
            elif self._regions_adjacent(client_region, va_region):
                return 0.5
            else:
                return 0.2
        except Exception:
            return 0.3

    def _get_region(self, timezone: str) -> str:
        """Map timezone to region."""
        tz = timezone.lower()
        if any(r in tz for r in ["america/new_york", "america/chicago", "america/denver", "america/los_angeles", "america/toronto"]):
            return "americas"
        if any(r in tz for r in ["europe/london", "europe/paris", "europe/berlin", "europe/moscow"]):
            return "europe"
        if any(r in tz for r in ["asia/tokyo", "asia/shanghai", "asia/singapore", "asia/hong_kong", "asia/seoul"]):
            return "asia_pacific"
        if any(r in tz for r in ["australia/sydney", "australia/melbourne", "pacific/auckland"]):
            return "oceania"
        return "other"

    def _regions_adjacent(self, r1: str, r2: str) -> bool:
        """Check if regions have reasonable overlap."""
        adjacent = {
            "americas": ["oceania"],
            "europe": ["africa", "asia_pacific"],
            "asia_pacific": ["oceania", "europe"],
            "oceania": ["americas", "asia_pacific"],
        }
        return r2 in adjacent.get(r1, [])


class SkillBasedMatcher:
    """Specialized matcher for specific skill combinations."""

    # Skill bundles for common roles
    ROLE_BUNDLES = {
        "executive_assistant": [
            "calendar management", "email management", "travel coordination",
            "meeting coordination", "expense tracking", "communication"
        ],
        "marketing_va": [
            "social media management", "content creation", "email marketing",
            "seo", "analytics", "canva design"
        ],
        "ecommerce_va": [
            "shopify management", "order processing", "customer service",
            "inventory management", "product listing", "returns processing"
        ],
        "operations_va": [
            "project management", "sop creation", "process documentation",
            "team coordination", "asana/notion setup", "workflow automation"
        ],
        "sales_va": [
            "lead generation", "cold outreach", "crm management",
            "appointment setting", "follow-up", "proposal creation"
        ],
    }

    @classmethod
    def detect_role(cls, skills: list[str]) -> str | None:
        """Detect role from skill list."""
        skill_set = set(s.lower() for s in skills)
        best_role = None
        best_score = 0

        for role, bundle in cls.ROLE_BUNDLES.items():
            bundle_set = set(bundle)
            overlap = skill_set & bundle_set
            score = len(overlap) / len(bundle_set)
            if score > best_score:
                best_score = score
                best_role = role

        return best_role if best_score > 0.3 else None

    @classmethod
    def get_missing_skills(cls, role: str, current_skills: list[str]) -> list[str]:
        """Get missing skills for a role."""
        if role not in cls.ROLE_BUNDLES:
            return []
        bundle = set(cls.ROLE_BUNDLES[role])
        current = set(s.lower() for s in current_skills)
        return list(bundle - current)


class MatchingService:
    """High-level matching service orchestrating the matching process."""

    def __init__(self, algorithm=None):
        self.algorithm = algorithm or DefaultMatchingAlgorithm()
        self.matcher = SkillBasedMatcher()

    async def match_client(
        self,
        client,
        va_pool: list,
        limit: int = 5,
        min_score: float = 0.4,
    ) -> list:
        """Find matches for a client."""
        matches = await self.algorithm.find_matches(client, va_pool, limit)

        # Filter by minimum score
        matches = [m for m in matches if m.match_score >= min_score]

        # Detect role and add role-specific insights
        role = self.matcher.detect_role(client.required_skills)
        for match in matches:
            match.match_factors["detected_role"] = role
            if role:
                va = next((v for v in va_pool if v.id == match.va_id), None)
                if va:
                    missing = self.matcher.get_missing_skills(role, [s.name for s in va.skills])
                    match.match_factors["missing_skills_for_role"] = missing

        return matches

    async def bulk_match(
        self,
        clients: list,
        va_pool: list,
        limit_per_client: int = 5,
    ) -> dict[str, list]:
        """Match multiple clients in parallel."""
        tasks = [self.match_client(c, va_pool, limit_per_client) for c in clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for i, client in enumerate(clients):
            result = results[i]
            if isinstance(result, list):
                output[client.id] = result
            else:
                log.error(f"Matching failed for client {client.id}: {result}")
                output[client.id] = []

        return output


# Backwards compatibility alias
MatchingAlgorithm = DefaultMatchingAlgorithm