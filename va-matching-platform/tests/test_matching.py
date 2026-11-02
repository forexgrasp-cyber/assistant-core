"""DefaultMatchingAlgorithm scoring — pure domain, no DB."""

from __future__ import annotations

from types import SimpleNamespace

from marketplace.base import VASkill, VAStatus
from marketplace.matching import DefaultMatchingAlgorithm, MatchWeights


def _client(**over):
    base = dict(
        id="client-1",
        required_skills=["admin", "bookkeeping"],
        max_hourly_rate=30.0,
        needed_hours_per_week=20,
        timezone="America/New_York",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _va(**over):
    base = dict(
        id="va-1",
        email="va@example.com",
        full_name="Test VA",
        timezone="America/New_York",
        hourly_rate=25.0,
        availability_hours_per_week=25,
        skills=[
            VASkill(name="Admin", category="admin", proficiency=4, years_experience=3),
            VASkill(name="Bookkeeping", category="finance", proficiency=4, years_experience=2),
        ],
        languages=["English"],
        location="NYC",
        bio="",
        portfolio_url="",
        linkedin_url="",
        status=VAStatus.ACTIVE,
        source="direct",
        source_profile_url="",
        source_rating=4.8,
        source_reviews_count=30,
        vetting_score=0.9,
        english_test_score=0.9,
        trial_task_score=0.8,
        reference_check_passed=True,
    )
    base.update(over)
    return SimpleNamespace(**base)


def weights_sum_to_one():
    w = MatchWeights()
    total = (
        w.skill_match
        + w.rate_fit
        + w.availability_fit
        + w.timezone_overlap
        + w.vetting_score
        + w.source_rating
    )
    assert abs(total - 1.0) < 1e-9


def same_timezone_perfect_fit_scores_high():
    algo = DefaultMatchingAlgorithm()
    score, factors = algo.calculate_match_score(_client(), _va())
    assert score > 0.6
    assert factors["skill_match"] == 1.0
    assert factors["timezone_overlap"] == 1.0
    assert factors["vetting_score"] == 0.9


def over_budget_va_penalized():
    algo = DefaultMatchingAlgorithm()
    _, cheap = algo.calculate_match_score(_client(), _va(hourly_rate=20.0))
    _, pricey = algo.calculate_match_score(_client(), _va(hourly_rate=90.0))
    assert cheap["rate_fit"] > pricey["rate_fit"]


async def unvetted_va_filtered_out():
    algo = DefaultMatchingAlgorithm()
    pool = [_va(status=VAStatus.PENDING), _va(vetting_score=0.2)]
    assert await algo.find_matches(_client(), pool) == []


async def matches_sorted_by_score():
    algo = DefaultMatchingAlgorithm()
    pool = [_va(id="weak", vetting_score=0.61), _va(id="strong", vetting_score=0.95)]
    matches = await algo.find_matches(_client(), pool, limit=5)
    assert [m.va_id for m in matches] == ["strong", "weak"]
