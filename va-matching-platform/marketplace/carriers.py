"""
Carriers & Logistics
====================
VA onboarding, delivery tracking, and fulfillment.
Patterned after marketplace-saas carriers.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

log = logging.getLogger(__name__)


class OnboardingStage(str, Enum):
    """VA onboarding stages."""
    APPLIED = "applied"
    ENGLISH_TEST = "english_test"
    TRIAL_TASK = "trial_task"
    REFERENCE_CHECK = "reference_check"
    VETTING_COMPLETE = "vetting_complete"
    PROFILE_APPROVED = "profile_approved"
    MATCHED = "matched"
    ONBOARDED = "onboarded"


class MatchStage(str, Enum):
    """Match progression stages."""
    PROPOSED = "proposed"
    INTRO_SENT = "intro_sent"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class OnboardingTask:
    """Individual onboarding task."""
    id: str
    title: str
    description: str
    assignee: str  # "client", "va", "platform"
    due_days: int  # Days from match acceptance
    required: bool = True
    completed: bool = False
    completed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OnboardingPlan:
    """Complete onboarding plan for a match."""
    match_id: str
    client_id: str
    va_id: str
    stage: OnboardingStage = OnboardingStage.VETTING_COMPLETE
    tasks: list[dict] = field(default_factory=list)  # OnboardingTask as dict
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_task_index: int = 0

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "client_id": self.client_id,
            "va_id": self.va_id,
            "stage": self.stage.value,
            "tasks": self.tasks,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_task_index": self.current_task_index,
        }


@dataclass
class DeliveryTracking:
    """Track VA work delivery."""
    id: str
    match_id: str
    task_id: str
    va_id: str
    client_id: str
    title: str
    description: str
    status: str = "pending"  # pending, in_progress, review, approved, rejected
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    hours_logged: float = 0.0
    deliverables: list[str] = field(default_factory=list)  # URLs to deliverables
    feedback: str = ""
    metadata: dict = field(default_factory=dict)


class OnboardingManager:
    """Manages VA onboarding workflow."""

    DEFAULT_CLIENT_TASKS = [
        {
            "id": "grant_access",
            "title": "Grant System Access",
            "description": "Grant VA access to all required tools (email, calendar, CRM, project management, password manager)",
            "assignee": "client",
            "due_days": 0,
            "required": True,
        },
        {
            "id": "share_sops",
            "title": "Share SOPs & Documentation",
            "description": "Share all relevant SOPs, process docs, brand guidelines, and templates",
            "assignee": "client",
            "due_days": 1,
            "required": True,
        },
        {
            "id": "setup_communication",
            "title": "Configure Communication Channels",
            "description": "Set up Slack/Teams, email delegation, calendar sharing, emergency contact",
            "assignee": "client",
            "due_days": 1,
            "required": True,
        },
        {
            "id": "define_priorities",
            "title": "Define Initial Priorities",
            "description": "List top 5 priorities for VA's first week with clear success criteria",
            "assignee": "client",
            "due_days": 2,
            "required": True,
        },
        {
            "id": "first_week_review",
            "title": "First Week Review Meeting",
            "description": "30-min review: what's working, what needs adjustment, priority updates",
            "assignee": "both",
            "due_days": 7,
            "required": True,
        },
        {
            "id": "thirty_day_review",
            "title": "30-Day Performance Review",
            "description": "Formal review: accomplishments, areas for improvement, priority updates for month 2",
            "assignee": "both",
            "due_days": 30,
            "required": True,
        },
    ]

    DEFAULT_VA_TASKS = [
        {
            "id": "verify_access",
            "title": "Verify System Access",
            "description": "Confirm access to all granted tools, report any issues",
            "assignee": "va",
            "due_days": 0,
            "required": True,
        },
        {
            "id": "review_sops",
            "title": "Review SOPs & Documentation",
            "description": "Read all shared SOPs, ask clarifying questions",
            "assignee": "va",
            "due_days": 2,
            "required": True,
        },
        {
            "id": "shadow_processes",
            "title": "Shadow Current Processes",
            "description": "Observe client's current workflows for key tasks",
            "assignee": "va",
            "due_days": 3,
            "required": True,
        },
        {
            "id": "first_deliverable",
            "title": "Complete First Independent Task",
            "description": "Execute first assigned task independently, submit for review",
            "assignee": "va",
            "due_days": 5,
            "required": True,
        },
        {
            "id": "weekly_update_template",
            "title": "Set Up Weekly Update Template",
            "description": "Create and share weekly update format with client",
            "assignee": "va",
            "due_days": 7,
            "required": True,
        },
    ]

    def __init__(self):
        self.plans: dict[str, Any] = {}  # match_id -> OnboardingPlan

    def create_plan(self, match_id: str, client_id: str, va_id: str) -> dict:
        """Create onboarding plan for a match."""
        plan = {
            "match_id": match_id,
            "client_id": client_id,
            "va_id": va_id,
            "stage": "vetting_complete",
            "tasks": [],
            "started_at": None,
            "completed_at": None,
            "current_task_index": 0,
        }

        # Add client tasks
        for task in self.DEFAULT_CLIENT_TASKS:
            plan["tasks"].append({
                **task,
                "id": f"client_{task['id']}",
                "completed": False,
                "completed_at": None,
            })

        # Add VA tasks
        for task in self.DEFAULT_VA_TASKS:
            plan["tasks"].append({
                **task,
                "id": f"va_{task['id']}",
                "completed": False,
                "completed_at": None,
            })

        self.plans[match_id] = plan
        return plan

    def start_onboarding(self, match_id: str) -> bool:
        """Mark onboarding as started."""
        if match_id not in self.plans:
            return False
        plan = self.plans[match_id]
        plan["stage"] = "onboarding"
        plan["started_at"] = datetime.now(UTC).isoformat()
        return True

    def complete_task(self, match_id: str, task_id: str, completed_by: str) -> bool:
        """Mark a task as completed."""
        if match_id not in self.plans:
            return False
        plan = self.plans[match_id]
        for task in plan["tasks"]:
            if task["id"] == task_id:
                task["completed"] = True
                task["completed_at"] = datetime.now(UTC).isoformat()
                task["completed_by"] = completed_by
                return True
        return False

    def get_progress(self, match_id: str) -> dict:
        """Get onboarding progress."""
        if match_id not in self.plans:
            return {"error": "Plan not found"}

        plan = self.plans[match_id]
        total = len(plan["tasks"])
        completed = sum(1 for t in plan["tasks"] if t.get("completed"))
        return {
            "match_id": match_id,
            "stage": plan["stage"],
            "total_tasks": total,
            "completed_tasks": completed,
            "progress_pct": round(completed / total * 100, 1) if total > 0 else 0,
            "tasks": plan["tasks"],
        }

    def advance_stage(self, match_id: str, new_stage: str) -> bool:
        """Advance onboarding stage."""
        if match_id not in self.plans:
            return False
        self.plans[match_id]["stage"] = new_stage
        if new_stage == "completed":
            self.plans[match_id]["completed_at"] = datetime.now(UTC).isoformat()
        return True


class DeliveryTracker:
    """Track VA work delivery and client feedback."""

    def __init__(self):
        self.deliveries: dict[str, list] = {}  # match_id -> list of deliveries

    def create_delivery(
        self,
        match_id: str,
        task_id: str,
        va_id: str,
        client_id: str,
        title: str,
        description: str,
    ) -> dict:
        delivery = {
            "id": str(uuid4()),
            "match_id": match_id,
            "task_id": task_id,
            "va_id": va_id,
            "client_id": client_id,
            "title": title,
            "description": description,
            "status": "pending",
            "submitted_at": None,
            "reviewed_at": None,
            "hours_logged": 0.0,
            "deliverables": [],
            "feedback": "",
            "metadata": {},
            "created_at": datetime.now(UTC).isoformat(),
        }

        if match_id not in self.deliveries:
            self.deliveries[match_id] = []
        self.deliveries[match_id].append(delivery)
        return delivery

    def submit_delivery(self, match_id: str, delivery_id: str, deliverables: list[str], hours: float) -> bool:
        """VA submits delivery."""
        for d in self.deliveries.get(match_id, []):
            if d["id"] == delivery_id:
                d["status"] = "submitted"
                d["submitted_at"] = datetime.now(UTC).isoformat()
                d["deliverables"] = deliverables
                d["hours_logged"] = hours
                return True
        return False

    def review_delivery(self, match_id: str, delivery_id: str, status: str, feedback: str = "") -> bool:
        """Client reviews delivery."""
        valid_statuses = ["approved", "rejected", "revision_requested"]
        if status not in valid_statuses:
            return False

        for d in self.deliveries.get(match_id, []):
            if d["id"] == delivery_id:
                d["status"] = status
                d["reviewed_at"] = datetime.now(UTC).isoformat()
                d["feedback"] = feedback
                return True
        return False

    def get_match_deliveries(self, match_id: str) -> list:
        return self.deliveries.get(match_id, [])

    def get_va_deliveries(self, va_id: str) -> list:
        all_deliveries = []
        for match_deliveries in self.deliveries.values():
            for d in match_deliveries:
                if d["va_id"] == va_id:
                    all_deliveries.append(d)
        return all_deliveries