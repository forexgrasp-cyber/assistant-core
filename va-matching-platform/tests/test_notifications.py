"""NotificationService in-app persistence (email disabled in tests)."""

from __future__ import annotations

from sqlalchemy import select

from marketplace.database.repositories import NotificationRepository, UserRepository
from marketplace.models import Notification, User
from marketplace.notifications import NotificationService


async def _make_user(db, user_id: str, email: str) -> User:
    """Create a platform user row for FK purposes."""
    repo = UserRepository(db)
    user = await repo.ensure_platform_user(user_id=user_id, email=email)
    await db.commit()
    return user


async def test_deliver_persists_notification(db):
    await _make_user(db, "00000000-0000-0000-0000-0000000000aa", "user1@va-matching.dev")
    svc = NotificationService()
    row = await svc.deliver_user_notification(
        db,
        user_id="00000000-0000-0000-0000-0000000000aa",
        kind="match_proposed",
        payload={"match_id": "m-1", "score": 0.8},
    )
    assert row is not None
    assert row.type == "match_proposed"
    assert row.title == "Match Proposed"
    assert "match" in row.message.lower()
    await db.commit()

    unread = await NotificationRepository(db).get_unread("00000000-0000-0000-0000-0000000000aa")
    assert len(unread) == 1
    assert unread[0].data["match_id"] == "m-1"


async def test_templated_body_used(db):
    await _make_user(db, "00000000-0000-0000-0000-0000000000bb", "user2@va-matching.dev")
    svc = NotificationService()
    row = await svc.deliver_user_notification(
        db, user_id="00000000-0000-0000-0000-0000000000bb", kind="monthly_fee_due"
    )
    assert row is not None
    assert row.message == "Monthly platform fee for this month is billed now."
    await db.commit()

    rows = (
        await db.execute(select(Notification).where(Notification.type == "monthly_fee_due"))
    ).scalars().all()
    assert len(rows) == 1


async def test_custom_title_and_body(db):
    await _make_user(db, "00000000-0000-0000-0000-0000000000cc", "user3@va-matching.dev")
    svc = NotificationService()
    row = await svc.deliver_user_notification(
        db,
        user_id="00000000-0000-0000-0000-0000000000cc",
        kind="custom",
        title="Hello",
        body="Custom body text",
    )
    assert row is not None
    assert row.title == "Hello"
    assert row.message == "Custom body text"
    await db.commit()