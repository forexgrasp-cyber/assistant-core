"""
Segment Service for CDP Engine
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Callable
from collections import defaultdict
import structlog

from ..config import get_cdp_settings
from ..models import (
    Segment, SegmentDefinition, SegmentRule, SegmentRuleOperator,
    SegmentRuleLogic, SegmentMembership, AudienceExport
)
from ..profiles.service import ProfileStore, ProfileService

logger = structlog.get_logger(__name__)


class SegmentEvaluator:
    """Evaluates segment rules against profiles."""

    def __init__(self, profile_store: ProfileStore):
        self.profile_store = profile_store

    async def evaluate_rule(self, profile: Any, rule: SegmentRule) -> bool:
        """Evaluate a single rule against a profile."""
        value = self._get_profile_value(profile, rule.field)
        if value is None:
            return rule.operator in [SegmentRuleOperator.NOT_EXISTS, SegmentRuleOperator.NOT_EQUALS]

        if rule.operator == SegmentRuleOperator.EQUALS:
            return value == rule.value
        elif rule.operator == SegmentRuleOperator.NOT_EQUALS:
            return value != rule.value
        elif rule.operator == SegmentRuleOperator.CONTAINS:
            return str(rule.value).lower() in str(value).lower()
        elif rule.operator == SegmentRuleOperator.NOT_CONTAINS:
            return str(rule.value).lower() not in str(value).lower()
        elif rule.operator == SegmentRuleOperator.STARTS_WITH:
            return str(value).lower().startswith(str(rule.value).lower())
        elif rule.operator == SegmentRuleOperator.ENDS_WITH:
            return str(value).lower().endswith(str(rule.value).lower())
        elif rule.operator == SegmentRuleOperator.GREATER_THAN:
            return self._compare(value, rule.value) > 0
        elif rule.operator == SegmentRuleOperator.LESS_THAN:
            return self._compare(value, rule.value) < 0
        elif rule.operator == SegmentRuleOperator.BETWEEN:
            if rule.values and len(rule.values) == 2:
                return self._compare(value, rule.values[0]) >= 0 and self._compare(value, rule.values[1]) <= 0
            return False
        elif rule.operator == SegmentRuleOperator.IN:
            return value in (rule.values or [])
        elif rule.operator == SegmentRuleOperator.NOT_IN:
            return value not in (rule.values or [])
        elif rule.operator == SegmentRuleOperator.EXISTS:
            return value is not None
        elif rule.operator == SegmentRuleOperator.NOT_EXISTS:
            return value is None
        elif rule.operator == SegmentRuleOperator.REGEX:
            import re
            return bool(re.match(str(rule.value), str(value)))
        elif rule.operator == SegmentRuleOperator.FUZZY:
            from rapidfuzz import fuzz
            return fuzz.ratio(str(value), str(rule.value)) / 100.0 >= 0.8

        return False

    def _get_profile_value(self, profile: Any, field: str) -> Any:
        """Get value from profile by field path."""
        # Handle nested fields like "attributes.key" or "custom_attributes.key"
        parts = field.split(".")
        obj = profile

        for part in parts:
            if obj is None:
                return None
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj

    def _compare(self, a: Any, b: Any) -> int:
        """Compare two values."""
        if a is None or b is None:
            return 0
        try:
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return (a > b) - (a < b)
            return (str(a) > str(b)) - (str(a) < str(b))
        except TypeError:
            return 0


class SegmentEngine:
    """Segment computation engine."""

    def __init__(
        self,
        profile_store: ProfileStore,
        profile_service: ProfileService,
        evaluator: SegmentEvaluator
    ):
        self.profile_store = profile_store
        self.profile_service = profile_service
        self.evaluator = evaluator
        self._segments: Dict[uuid.UUID, Segment] = {}
        self._definitions: Dict[uuid.UUID, SegmentDefinition] = {}
        self._computation_locks: Dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def create_segment(self, definition: SegmentDefinition) -> Segment:
        """Create a new segment."""
        segment = Segment(
            segment_id=definition.segment_id,
            definition=definition,
        )
        self._segments[definition.segment_id] = segment
        self._definitions[definition.segment_id] = definition
        logger.info("segment_created", segment_id=str(definition.segment_id), name=definition.name)
        return segment

    async def get_segment(self, segment_id: uuid.UUID) -> Optional[Segment]:
        """Get segment by ID."""
        return self._segments.get(segment_id)

    async def get_definition(self, segment_id: uuid.UUID) -> Optional[SegmentDefinition]:
        """Get segment definition by ID."""
        return self._definitions.get(segment_id)

    async def compute_segment(self, segment_id: uuid.UUID) -> Segment:
        """Compute segment membership."""
        segment = self._segments.get(segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

        lock = self._computation_locks[segment_id]
        async with lock:
            segment.status = "computing"
            start_time = datetime.utcnow()

            try:
                # Get all profiles
                profiles = list(self.profile_store._profiles.values())

                # Evaluate rules for each profile
                member_ids = set()
                for profile in profiles:
                    if await self._evaluate_profile(profile, segment.definition):
                        member_ids.add(profile.profile_id)

                # Update segment
                segment.member_ids = list(member_ids)
                segment.member_count = len(member_ids)
                segment.estimated_size = len(member_ids)
                segment.last_computed = datetime.utcnow()
                segment.computation_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                segment.status = "ready"

                # Update profile segment memberships
                await self._update_memberships(segment)

                logger.info(
                    "segment_computed",
                    segment_id=str(segment_id),
                    member_count=segment.member_count,
                    computation_time_ms=segment.computation_time_ms,
                )

            except Exception as e:
                segment.status = "failed"
                segment.error = str(e)
                logger.error("segment_computation_failed", segment_id=str(segment_id), error=str(e))
                raise

            return segment

    async def _evaluate_profile(self, profile: Any, definition: SegmentDefinition) -> bool:
        """Evaluate all rules for a profile."""
        if not definition.rules:
            return False

        results = []
        for rule in definition.rules:
            result = await self.evaluator.evaluate_rule(profile, rule)
            results.append(result)

        # Apply logic
        if definition.logic == SegmentRuleLogic.AND:
            return all(results)
        elif definition.logic == SegmentRuleLogic.OR:
            return any(results)
        elif definition.logic == SegmentRuleLogic.NOT:
            return not any(results)

        return False

    async def _update_memberships(self, segment: Segment) -> None:
        """Update profile segment memberships."""
        segment_id = segment.segment_id
        member_ids = set(segment.member_ids)

        # Get current members
        current_members = set()
        if segment_id in self.profile_store._segment_memberships:
            current_members = self.profile_store._segment_memberships[segment_id].copy()

        # Add new members
        new_members = member_ids - current_members
        for profile_id in new_members:
            await self.profile_store.add_segment_membership(profile_id, segment_id)

        # Remove old members
        removed_members = current_members - member_ids
        for profile_id in removed_members:
            await self.profile_store.remove_segment_membership(profile_id, segment_id)

        # Create membership records
        for profile_id in member_ids:
            membership = SegmentMembership(
                profile_id=profile_id,
                segment_id=segment_id,
                joined_at=datetime.utcnow(),
                is_active=True,
            )
            # Store membership (in production, would persist to DB)


class SegmentService:
    """High-level segment service."""

    def __init__(self, engine: SegmentEngine, profile_service: ProfileService):
        self.engine = engine
        self.profile_service = profile_service
        self._scheduled_refresh: Dict[uuid.UUID, asyncio.Task] = {}

    async def create_segment(self, definition: SegmentDefinition) -> Segment:
        """Create a new segment."""
        return await self.engine.create_segment(definition)

    async def get_segment(self, segment_id: uuid.UUID) -> Optional[Segment]:
        """Get segment by ID."""
        return await self.engine.get_segment(segment_id)

    async def compute_segment(self, segment_id: uuid.UUID) -> Segment:
        """Compute segment membership."""
        return await self.engine.compute_segment(segment_id)

    async def get_segment_members(self, segment_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get segment members."""
        segment = await self.engine.get_segment(segment_id)
        if segment:
            return set(segment.member_ids)
        return set()

    async def export_audience(self, request: AudienceExport) -> Dict[str, Any]:
        """Export audience to file."""
        segment = await self.engine.get_segment(request.segment_id)
        if not segment:
            raise ValueError(f"Segment {request.segment_id} not found")

        # Get member profiles
        profiles = []
        for member_id in segment.member_ids:
            profile = await self.profile_service.get_profile(member_id)
            if profile:
                profiles.append(profile)

        # Filter fields if requested
        if request.fields:
            filtered_profiles = []
            for profile in profiles:
                filtered = {field: getattr(profile, field, None) for field in request.fields}
                filtered_profiles.append(filtered)
            profiles = filtered_profiles

        # Apply filters if requested
        if request.filters:
            # Apply additional filters
            pass

        # Format output
        if request.format == "json":
            import json
            content = json.dumps([p.model_dump() for p in profiles], default=str)
        elif request.format == "csv":
            import csv
            import io
            output = io.StringIO()
            if profiles:
                writer = csv.DictWriter(output, fieldnames=profiles[0].keys())
                writer.writeheader()
                for p in profiles:
                    writer.writerow(p)
            content = output.getvalue()
        else:
            content = str(profiles)

        # Save to destination if provided
        if request.destination:
            # Save to S3, GCS, FTP, etc.
            pass

        return {
            "segment_id": str(request.segment_id),
            "format": request.format,
            "member_count": len(profiles),
            "content": content,
        }

    async def schedule_refresh(self, segment_id: uuid.UUID, interval_seconds: int) -> None:
        """Schedule automatic segment refresh."""
        if segment_id in self._scheduled_refresh:
            self._scheduled_refresh[segment_id].cancel()

        async def refresh_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.engine.compute_segment(segment_id)
                except Exception as e:
                    logger.error("scheduled_refresh_failed", segment_id=str(segment_id), error=str(e))

        task = asyncio.create_task(refresh_loop())
        self._scheduled_refresh[segment_id] = task
        logger.info("segment_refresh_scheduled", segment_id=str(segment_id), interval=interval_seconds)

    async def cancel_refresh(self, segment_id: uuid.UUID) -> None:
        """Cancel scheduled refresh."""
        if segment_id in self._scheduled_refresh:
            self._scheduled_refresh[segment_id].cancel()
            del self._scheduled_refresh[segment_id]
            logger.info("segment_refresh_cancelled", segment_id=str(segment_id))


from collections import defaultdict