"""VettingService — pure domain on base dataclasses."""

from __future__ import annotations

from marketplace.base import VASkill, VAProfile, VAStatus
from marketplace.vetting import VettingService


def _profile(**over) -> VAProfile:
    p = VAProfile(
        id="va-vet-1",
        email="vet@example.com",
        full_name="Vet Me",
        timezone="Europe/London",
        hourly_rate=22.0,
        availability_hours_per_week=30,
        skills=[VASkill(name="Admin", category="admin", proficiency=4)],
        languages=["English"],
        location="London",
        bio="",
        portfolio_url="",
        linkedin_url="",
        status=VAStatus.PENDING,
        source="direct",
        source_profile_url="",
        source_rating=4.5,
        source_reviews_count=12,
        vetting_score=0.0,
        english_test_score=0.0,
        trial_task_score=0.0,
        reference_check_passed=False,
    )
    for k, v in over.items():
        setattr(p, k, v)
    return p


async def vet_returns_scored_profile():
    svc = VettingService()
    scored = await svc.vet_va(_profile())
    assert 0.0 <= scored.vetting_score <= 1.0
    assert scored.status in (VAStatus.PENDING, VAStatus.VETTING, VAStatus.ACTIVE)


async def bulk_vet_preserves_count():
    svc = VettingService()
    profiles = [_profile(id=f"va-{i}") for i in range(3)]
    scored = await svc.bulk_vet(profiles)
    assert len(scored) == 3
