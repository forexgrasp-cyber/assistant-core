"""Seed achievement definitions into the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.gamification import Achievement, AchievementCategory


ACHIEVEMENTS = [
    # Streak Achievements
    {
        "id": "streak_3",
        "key": "streak_3",
        "name": "Getting Started",
        "description": "Maintain a 3-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "fire",
        "xp_reward": 50,
        "gems_reward": 5,
        "criteria": {"streak_days": 3},
        "is_hidden": False,
    },
    {
        "id": "streak_7",
        "key": "streak_7",
        "name": "Week Warrior",
        "description": "Maintain a 7-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "zap",
        "xp_reward": 150,
        "gems_reward": 15,
        "criteria": {"streak_days": 7},
        "is_hidden": False,
    },
    {
        "id": "streak_14",
        "key": "streak_14",
        "name": "Fortnight Fighter",
        "description": "Maintain a 14-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "flame",
        "xp_reward": 300,
        "gems_reward": 30,
        "criteria": {"streak_days": 14},
        "is_hidden": False,
    },
    {
        "id": "streak_30",
        "key": "streak_30",
        "name": "Monthly Master",
        "description": "Maintain a 30-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "crown",
        "xp_reward": 1000,
        "gems_reward": 100,
        "criteria": {"streak_days": 30},
        "is_hidden": False,
    },
    {
        "id": "streak_100",
        "key": "streak_100",
        "name": "Centurion",
        "description": "Maintain a 100-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "medal",
        "xp_reward": 5000,
        "gems_reward": 500,
        "criteria": {"streak_days": 100},
        "is_hidden": False,
    },
    {
        "id": "streak_365",
        "key": "streak_365",
        "name": "Legendary",
        "description": "Maintain a 365-day streak",
        "category": AchievementCategory.STREAK,
        "icon": "star",
        "xp_reward": 20000,
        "gems_reward": 2000,
        "criteria": {"streak_days": 365},
        "is_hidden": False,
    },

    # Progress Achievements
    {
        "id": "first_lesson",
        "key": "first_lesson",
        "name": "First Steps",
        "description": "Complete your first lesson",
        "category": AchievementCategory.PROGRESS,
        "icon": "graduation-cap",
        "xp_reward": 25,
        "gems_reward": 2,
        "criteria": {"lessons_completed": 1},
        "is_hidden": False,
    },
    {
        "id": "lessons_10",
        "key": "lessons_10",
        "name": "Scholar",
        "description": "Complete 10 lessons",
        "category": AchievementCategory.PROGRESS,
        "icon": "book-open",
        "xp_reward": 200,
        "gems_reward": 20,
        "criteria": {"lessons_completed": 10},
        "is_hidden": False,
    },
    {
        "id": "lessons_50",
        "key": "lessons_50",
        "name": "Bookworm",
        "description": "Complete 50 lessons",
        "category": AchievementCategory.PROGRESS,
        "icon": "library",
        "xp_reward": 1000,
        "gems_reward": 100,
        "criteria": {"lessons_completed": 50},
        "is_hidden": False,
    },
    {
        "id": "lessons_100",
        "key": "lessons_100",
        "name": "Polyglot",
        "description": "Complete 100 lessons",
        "category": AchievementCategory.PROGRESS,
        "icon": "globe",
        "xp_reward": 3000,
        "gems_reward": 300,
        "criteria": {"lessons_completed": 100},
        "is_hidden": False,
    },
    {
        "id": "level_10",
        "key": "level_10",
        "name": "Rising Star",
        "description": "Reach level 10",
        "category": AchievementCategory.PROGRESS,
        "icon": "trending-up",
        "xp_reward": 500,
        "gems_reward": 50,
        "criteria": {"level": 10},
        "is_hidden": False,
    },
    {
        "id": "level_25",
        "key": "level_25",
        "name": "Veteran",
        "description": "Reach level 25",
        "category": AchievementCategory.PROGRESS,
        "icon": "shield",
        "xp_reward": 2000,
        "gems_reward": 200,
        "criteria": {"level": 25},
        "is_hidden": False,
    },
    {
        "id": "level_50",
        "key": "level_50",
        "name": "Grandmaster",
        "description": "Reach level 50",
        "category": AchievementCategory.PROGRESS,
        "icon": "diamond",
        "xp_reward": 10000,
        "gems_reward": 1000,
        "criteria": {"level": 50},
        "is_hidden": False,
    },

    # Mastery Achievements
    {
        "id": "perfect_5",
        "key": "perfect_5",
        "name": "Perfectionist",
        "description": "Complete 5 lessons with 100% accuracy",
        "category": AchievementCategory.MASTERY,
        "icon": "target",
        "xp_reward": 250,
        "gems_reward": 25,
        "criteria": {"perfect_lessons": 5},
        "is_hidden": False,
    },
    {
        "id": "perfect_20",
        "key": "perfect_20",
        "name": "Flawless",
        "description": "Complete 20 lessons with 100% accuracy",
        "category": AchievementCategory.MASTERY,
        "icon": "check-circle",
        "xp_reward": 1000,
        "gems_reward": 100,
        "criteria": {"perfect_lessons": 20},
        "is_hidden": False,
    },

    # League Achievements
    {
        "id": "league_silver",
        "key": "league_silver",
        "name": "Silver Tongue",
        "description": "Reach Silver league",
        "category": AchievementCategory.PROGRESS,
        "icon": "medal",
        "xp_reward": 500,
        "gems_reward": 50,
        "criteria": {"league_tier": "silver"},
        "is_hidden": False,
    },
    {
        "id": "league_gold",
        "key": "league_gold",
        "name": "Golden Voice",
        "description": "Reach Gold league",
        "category": AchievementCategory.PROGRESS,
        "icon": "trophy",
        "xp_reward": 1500,
        "gems_reward": 150,
        "criteria": {"league_tier": "gold"},
        "is_hidden": False,
    },
    {
        "id": "league_diamond",
        "key": "league_diamond",
        "name": "Diamond Speaker",
        "description": "Reach Diamond league",
        "category": AchievementCategory.PROGRESS,
        "icon": "gem",
        "xp_reward": 5000,
        "gems_reward": 500,
        "criteria": {"league_tier": "diamond"},
        "is_hidden": False,
    },
    {
        "id": "league_obsidian",
        "key": "league_obsidian",
        "name": "Obsidian Oracle",
        "description": "Reach Obsidian league (top 1%)",
        "category": AchievementCategory.PROGRESS,
        "icon": "crown",
        "xp_reward": 20000,
        "gems_reward": 2000,
        "criteria": {"league_tier": "obsidian"},
        "is_hidden": False,
    },

    # Social Achievements
    {
        "id": "friend_1",
        "key": "friend_1",
        "name": "Social Butterfly",
        "description": "Add your first friend",
        "category": AchievementCategory.SOCIAL,
        "icon": "users",
        "xp_reward": 50,
        "gems_reward": 5,
        "criteria": {"friends_count": 1},
        "is_hidden": False,
    },
    {
        "id": "friend_10",
        "key": "friend_10",
        "name": "Popular",
        "description": "Have 10 friends",
        "category": AchievementCategory.SOCIAL,
        "icon": "heart",
        "xp_reward": 500,
        "gems_reward": 50,
        "criteria": {"friends_count": 10},
        "is_hidden": False,
    },

    # Exploration Achievements
    {
        "id": "language_2",
        "key": "language_2",
        "name": "Bilingual",
        "description": "Start learning a second language",
        "category": AchievementCategory.EXPLORATION,
        "icon": "languages",
        "xp_reward": 200,
        "gems_reward": 20,
        "criteria": {"languages_started": 2},
        "is_hidden": False,
    },
    {
        "id": "language_5",
        "key": "language_5",
        "name": "Polyglot Explorer",
        "description": "Start learning 5 languages",
        "category": AchievementCategory.EXPLORATION,
        "icon": "map",
        "xp_reward": 1000,
        "gems_reward": 100,
        "criteria": {"languages_started": 5},
        "is_hidden": False,
    },
    {
        "id": "human_tutor_first",
        "key": "human_tutor_first",
        "name": "Conversation Partner",
        "description": "Complete your first human tutor session",
        "category": AchievementCategory.EXPLORATION,
        "icon": "user-check",
        "xp_reward": 500,
        "gems_reward": 50,
        "criteria": {"human_tutor_sessions": 1},
        "is_hidden": False,
    },

    # Dedication Achievements
    {
        "id": "xp_10000",
        "key": "xp_10000",
        "name": "Dedicated Learner",
        "description": "Earn 10,000 total XP",
        "category": AchievementCategory.DEDICATION,
        "icon": "zap",
        "xp_reward": 1000,
        "gems_reward": 100,
        "criteria": {"total_xp": 10000},
        "is_hidden": False,
    },
    {
        "id": "xp_100000",
        "key": "xp_100000",
        "name": "XP Millionaire",
        "description": "Earn 100,000 total XP",
        "category": AchievementCategory.DEDICATION,
        "icon": "coins",
        "xp_reward": 10000,
        "gems_reward": 1000,
        "criteria": {"total_xp": 100000},
        "is_hidden": False,
    },
    {
        "id": "gems_1000",
        "key": "gems_1000",
        "name": "Gem Collector",
        "description": "Earn 1,000 gems total",
        "category": AchievementCategory.DEDICATION,
        "icon": "gem",
        "xp_reward": 2000,
        "gems_reward": 200,
        "criteria": {"gems_earned": 1000},
        "is_hidden": False,
    },

    # Hidden/Secret Achievements
    {
        "id": "night_owl",
        "key": "night_owl",
        "name": "Night Owl",
        "description": "Complete a lesson after midnight",
        "category": AchievementCategory.EXPLORATION,
        "icon": "moon",
        "xp_reward": 100,
        "gems_reward": 10,
        "criteria": {"night_lesson": True},
        "is_hidden": True,
    },
    {
        "id": "early_bird",
        "key": "early_bird",
        "name": "Early Bird",
        "description": "Complete a lesson before 6 AM",
        "category": AchievementCategory.EXPLORATION,
        "icon": "sunrise",
        "xp_reward": 100,
        "gems_reward": 10,
        "criteria": {"early_lesson": True},
        "is_hidden": True,
    },
    {
        "id": "weekend_warrior",
        "key": "weekend_warrior",
        "name": "Weekend Warrior",
        "description": "Complete 10 lessons on weekends",
        "category": AchievementCategory.DEDICATION,
        "icon": "calendar",
        "xp_reward": 500,
        "gems_reward": 50,
        "criteria": {"weekend_lessons": 10},
        "is_hidden": True,
    },
]


async def seed_achievements():
    """Seed achievement definitions."""
    async with AsyncSessionLocal() as db:
        for ach_data in ACHIEVEMENTS:
            # Check if already exists
            result = await db.execute(select(Achievement).where(Achievement.id == ach_data["id"]))
            existing = result.scalar_one_or_none()
            if existing:
                print(f"Achievement {ach_data['id']} already exists, skipping")
                continue

            achievement = Achievement(**ach_data)
            db.add(achievement)
            print(f"Added achievement: {ach_data['name']} ({ach_data['id']})")

        await db.commit()
        print(f"\nSeeded {len(ACHIEVEMENTS)} achievements!")


if __name__ == "__main__":
    asyncio.run(seed_achievements())