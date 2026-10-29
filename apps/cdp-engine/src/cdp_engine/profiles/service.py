import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import structlog

from ..config import get_cdp_settings
from ..models import (
    UnifiedProfile, ProfileUpdate, SegmentRule, SegmentDefinition,
    Segment, SegmentMembership, ProfileEvent, IdentitySource, IdentityType
)
from ..identity.resolver import IdentityIndex

logger = structlog.get_logger(__name__)


class ProfileStore:
    """In-memory profile store with Redis backup."""

    def __init__(self):
        self._profiles: Dict[uuid.UUID, UnifiedProfile] = {}
        self._identity_index = IdentityIndex()
        self._segment_memberships: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
        self._profile_segments: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
        self._version_locks: Dict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def create(self, profile: UnifiedProfile) -> UnifiedProfile:
        """Create a new profile."""
        self._profiles[profile.profile_id] = profile
        self._index_identities(profile)
        logger.info("profile_created", profile_id=str(profile.profile_id))
        return profile

    async def get(self, profile_id: uuid.UUID) -> Optional[UnifiedProfile]:
        """Get profile by ID."""
        return self._profiles.get(profile_id)

    async def get_by_identity(self, identity: Any) -> Optional[UnifiedProfile]:
        """Get profile by identity."""
        profile_id = self._identity_index.lookup(identity)
        if profile_id:
            return self._profiles.get(profile_id)
        return None

    async def update(self, update: ProfileUpdate) -> Optional[UnifiedProfile]:
        """Update profile with optimistic locking."""
        lock = self._version_locks[update.profile_id]
        async with lock:
            profile = self._profiles.get(update.profile_id)
            if not profile:
                return None

            if profile.version != update.version:
                raise ValueError("Version mismatch - profile was modified")

            # Update attributes
            if update.attributes:
                profile.attributes.update(update.attributes)
            if update.custom_attributes:
                profile.custom_attributes.update(update.custom_attributes)
            if update.identities:
                # Remove old identities from index
                for identity in profile.identities:
                    self._identity_index.remove(profile.profile_id, identity)
                # Add new identities
                profile.identities = update.identities
                self._index_identities(profile)

            if update.consent_updates:
                profile.consent_status.update(update.consent_updates)

            profile.version += 1
            profile.updated_at = datetime.utcnow()

            logger.info("profile_updated", profile_id=str(update.profile_id), version=profile.version)
            return profile

    async def delete(self, profile_id: uuid.UUID) -> bool:
        """Delete profile."""
        profile = self._profiles.pop(profile_id, None)
        if profile:
            for identity in profile.identities:
                self._identity_index.remove(profile_id, identity)
            self._profile_segments.pop(profile_id, None)
            for segment_id in self._segment_memberships:
                self._segment_memberships[segment_id].discard(profile_id)
            logger.info("profile_deleted", profile_id=str(profile_id))
            return True
        return False

    async def merge(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        strategy: str = "merge_attributes"
    ) -> Optional[UnifiedProfile]:
        """Merge two profiles."""
        source = self._profiles.get(source_id)
        target = self._profiles.get(target_id)

        if not source or not target:
            return None

        if strategy == "keep_target":
            # Move identities to target
            for identity in source.identities:
                self._identity_index.remove(source_id, identity)
                self._identity_index.add(target_id, identity)
                target.identities.append(identity)
            # Merge attributes
            if strategy == "merge_attributes":
                target.attributes.update(source.attributes)
                target.custom_attributes.update(source.custom_attributes)
        elif strategy == "keep_source":
            return await self.merge(target_id, source_id, strategy)

        # Update segment memberships
        for segment_id in self._profile_segments[source_id]:
            self._segment_memberships[segment_id].discard(source_id)
            self._segment_memberships[segment_id].add(target_id)

        for segment_id in self._profile_segments[source_id]:
            self._profile_segments[target_id].add(segment_id)

        # Delete source
        await self.delete(source_id)

        logger.info("profiles_merged", source_id=str(source_id), target_id=str(target_id))
        return target

    async def split(
        self,
        profile_id: uuid.UUID,
        identities_to_move: List[Any],
        new_profile_attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Any]:
        """Split a profile into two."""
        source = self._profiles.get(profile_id)
        if not source:
            return None, None

        # Create new profile
        new_profile = UnifiedProfile(
            identities=identities_to_move,
            attributes=new_profile_attributes or {},
        )
        self._profiles[new_profile.profile_id] = new_profile
        self._index_identities(new_profile)

        # Remove identities from source
        for identity in identities_to_move:
            self._identity_index.remove(profile_id, identity)
            source.identities = [i for i in source.identities if i.identifier != identity.identifier]

        # Update segment memberships
        # (In production, would re-evaluate segment membership)

        logger.info("profile_split", source_id=str(profile_id), new_id=str(new_profile.profile_id))
        return source, new_profile

    def _index_identities(self, profile: UnifiedProfile) -> None:
        """Index all identities for a profile."""
        for identity in profile.identities:
            self._identity_index.add(profile.profile_id, identity)

    async def add_segment_membership(self, profile_id: uuid.UUID, segment_id: uuid.UUID) -> None:
        """Add profile to segment."""
        self._segment_memberships[segment_id].add(profile_id)
        self._profile_segments[profile_id].add(segment_id)

    async def remove_segment_membership(self, profile_id: uuid.UUID, segment_id: uuid.UUID) -> None:
        """Remove profile from segment."""
        self._segment_memberships[segment_id].discard(profile_id)
        self._profile_segments[profile_id].discard(segment_id)

    async def get_segment_members(self, segment_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get all members of a segment."""
        return self._segment_memberships.get(segment_id, set())

    async def get_profile_segments(self, profile_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get all segments for a profile."""
        return self._profile_segments.get(profile_id, set())


import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from collections import defaultdict
import structlog

from ..config import get_cdp_settings
from ..models import (
    UnifiedProfile, ProfileUpdate, SegmentRule, SegmentDefinition,
    Segment, SegmentMembership, ProfileEvent, IdentitySource, IdentityType
)
from ..identity.resolver import IdentityIndex

class ProfileService:
    """High-level profile service with streaming integration."""

    def __init__(self, store: ProfileStore, resolver: Any = None):
        self.store = store
        self.resolver = resolver
        self._event_handlers: Dict[str, List[Callable[[Any], Any]]] = defaultdict(list)

    async def create_profile(self, profile: UnifiedProfile) -> UnifiedProfile:
        """Create a new profile."""
        # Check for existing profile with same identities
        if self.resolver:
            for identity in profile.identities:
                existing = await self.store.get_by_identity(identity)
                if existing:
                    # Merge with existing
                    merged = await self.store.merge(profile.profile_id, existing.profile_id)
                    if merged:
                        return merged
                    # If merge failed, return existing profile
                    return existing

        return await self.store.create(profile)

    async def get_profile(self, profile_id: uuid.UUID) -> Optional[UnifiedProfile]:
        """Get profile by ID."""
        return await self.store.get(profile_id)

    async def get_profile_by_identity(self, identity: Any) -> Optional[UnifiedProfile]:
        """Get profile by identity."""
        return await self.store.get_by_identity(identity)

    async def update_profile(self, update: ProfileUpdate) -> Optional[UnifiedProfile]:
        """Update profile."""
        profile = await self.store.update(update)
        if profile:
            await self._emit_event(ProfileEvent(
                event_type="updated",
                profile_id=update.profile_id,
                changes=update.attributes,
            ))
        return profile

    async def delete_profile(self, profile_id: uuid.UUID) -> bool:
        """Delete profile."""
        result = await self.store.delete(profile_id)
        if result:
            await self._emit_event(ProfileEvent(
                event_type="deleted",
                profile_id=profile_id,
            ))
        return result

    async def merge_profiles(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        strategy: str = "merge_attributes"
    ) -> Optional[UnifiedProfile]:
        """Merge two profiles."""
        result = await self.store.merge(source_id, target_id, strategy)
        if result:
            await self._emit_event(ProfileEvent(
                event_type="merged",
                profile_id=target_id,
                changes={"merged_from": str(source_id)},
            ))
        return result

    async def split_profile(
        self,
        profile_id: uuid.UUID,
        identities_to_move: List[Any],
        new_profile_attributes: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Any], Optional[Any]]:
        """Split a profile."""
        return await self.store.split(profile_id, identities_to_move, new_profile_attributes)

    async def enrich_profile(self, profile_id: uuid.UUID, data: Dict[str, Any], source: str) -> Optional[UnifiedProfile]:
        """Enrich profile with external data."""
        profile = await self.store.get(profile_id)
        if not profile:
            return None

        profile.enriched_data.update(data)
        if source not in profile.enrichment_sources:
            profile.enrichment_sources.append(source)
        profile.last_enriched = datetime.utcnow()
        profile.updated_at = datetime.utcnow()

        await self._emit_event(ProfileEvent(
            event_type="enriched",
            profile_id=profile_id,
            changes={"enrichment_source": source},
        ))

        return profile

    async def add_to_segment(self, profile_id: uuid.UUID, segment_id: uuid.UUID) -> None:
        """Add profile to segment."""
        await self.store.add_segment_membership(profile_id, segment_id)

    async def remove_from_segment(self, profile_id: uuid.UUID, segment_id: uuid.UUID) -> None:
        """Remove profile from segment."""
        await self.store.remove_segment_membership(profile_id, segment_id)

    async def get_segment_members(self, segment_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get all members of a segment."""
        return await self.store.get_segment_members(segment_id)

    async def get_profile_segments(self, profile_id: uuid.UUID) -> Set[uuid.UUID]:
        """Get all segments for a profile."""
        return await self.store.get_profile_segments(profile_id)

    def on_event(self, event_type: str, handler: Callable[[Any], Any]) -> None:
        """Register event handler."""
        self._event_handlers[event_type].append(handler)

    async def _emit_event(self, event: ProfileEvent) -> None:
        """Emit profile event to handlers."""
        for handler in self._event_handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error("event_handler_failed", event_type=event.event_type, error=str(e))

    async def process_streaming_event(self, event: Any) -> None:
        """Process event from streaming engine."""
        # Extract identities from event
        identities = []
        if event.user:
            if event.user.user_id:
                identities.append(IdentitySource(
                    source=event.source or "streaming",
                    identifier=event.user.user_id,
                    identity_type=IdentityType.USER_ID,
                ))
            if event.user.anonymous_id:
                identities.append(IdentitySource(
                    source=event.source or "streaming",
                    identifier=event.user.anonymous_id,
                    identity_type=IdentityType.ANONYMOUS_ID,
                ))
            if event.user.email:
                identities.append(IdentitySource(
                    source=event.source or "streaming",
                    identifier=event.user.email,
                    identity_type=IdentityType.EMAIL,
                ))

        if not identities:
            return

        # Resolve or create profile
        profile = await self.get_profile_by_identity(identities[0])
        if not profile:
            profile = UnifiedProfile(identities=identities)
            await self.store.create(profile)
        else:
            # Update last seen
            profile.last_seen = datetime.utcnow()
            profile.event_count += 1
            profile.updated_at = datetime.utcnow()
            await self.store.update(ProfileUpdate(
                profile_id=profile.profile_id,
                version=profile.version,
            ))

            # Add new identities if not present
            for identity in identities:
                if not any(i.identifier == identity.identifier for i in profile.identities):
                    profile.identities.append(identity)
                    self.store._identity_index.add(profile.profile_id, identity)