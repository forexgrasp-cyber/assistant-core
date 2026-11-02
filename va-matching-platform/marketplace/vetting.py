"""
VA Vetting Workflow
====================
Complete VA vetting pipeline: English test, trial task, reference check.
"""

from __future__ import annotations

import asyncio
import logging
import random
import string
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base import VAProfile, VAStatus, VettingWorkflow

log = logging.getLogger(__name__)


@dataclass
class EnglishTest:
    """English proficiency test."""
    id: str
    type: str  # "standard", "advanced", "business"
    questions: list[dict]  # {question, type, answer, points}
    time_limit_minutes: int
    passing_score: float = 0.75


@dataclass
class TrialTask:
    """Trial task for VA assessment."""
    id: str
    title: str
    description: str
    category: str  # admin, marketing, ecommerce, operations, sales
    difficulty: str  # easy, medium, hard
    estimated_hours: float
    evaluation_criteria: list[str]
    max_score: float = 100.0


@dataclass
class ReferenceCheck:
    """Reference check result."""
    reference_name: str
    reference_email: str
    relationship: str
    years_known: float
    rating: float  # 1-5
    strengths: list[str]
    weaknesses: list[str]
    would_rehire: bool
    comments: str
    verified: bool = False


class EnglishTestBank:
    """Bank of English test questions."""

    TESTS = {
        "standard": EnglishTest(
            id="english_standard",
            type="standard",
            time_limit_minutes=30,
            passing_score=0.75,
            questions=[
                {"id": "q1", "type": "multiple_choice", "question": "Choose the correct sentence:",
                 "options": ["She don't like coffee.", "She doesn't like coffee.", "She not like coffee."],
                 "answer": 1, "points": 10},
                {"id": "q2", "type": "multiple_choice", "question": "Choose the correct form:",
                 "options": ["I have been working here since 2020.", "I am working here since 2020.", "I work here since 2020."],
                 "answer": 0, "points": 10},
                {"id": "q3", "type": "fill_blank", "question": "Please _____ the report by Friday.",
                 "answer": "submit", "points": 10},
                {"id": "q4", "type": "multiple_choice", "question": "Which is most professional?",
                 "options": ["Hey, can u send me the file?", "Could you please send me the file?", "Send file pls."],
                 "answer": 1, "points": 10},
                {"id": "q5", "type": "reading", "question": "Read and answer: 'The meeting was rescheduled to 3 PM due to a conflict.' When is the meeting?",
                 "answer": "3 PM", "points": 10},
                {"id": "q6", "type": "writing", "question": "Write a professional email confirming a 2 PM meeting tomorrow.",
                 "answer": "keywords: confirm, 2 PM, tomorrow, meeting", "points": 20},
                {"id": "q7", "type": "listening", "question": "Audio: 'Please review the attached document and provide feedback by EOD.' What is the deadline?",
                 "answer": "EOD / end of day", "points": 10},
                {"id": "q8", "type": "multiple_choice", "question": "Choose the correct preposition: 'The deadline is ____ Friday.'",
                 "options": ["in", "on", "at", "by"], "answer": 1, "points": 10},
                {"id": "q9", "type": "correction", "question": "Correct: 'I am agree with your proposal.'",
                 "answer": "I agree with your proposal.", "points": 10},
                {"id": "q10", "type": "writing", "question": "Write a brief status update for a client (3-4 sentences).",
                 "answer": "keywords: progress, completed, next steps, timeline", "points": 20},
            ]
        ),
        "advanced": EnglishTest(
            id="english_advanced",
            type="advanced",
            time_limit_minutes=45,
            passing_score=0.8,
            questions=[
                # More complex business English questions
            ]
        ),
    }

    @classmethod
    def get_test(cls, test_type: str = "standard") -> EnglishTest:
        return cls.TESTS.get(test_type, cls.TESTS["standard"])


class TrialTaskBank:
    """Bank of trial tasks by category."""

    TASKS = {
        "admin": [
            TrialTask(
                id="admin_calendar",
                title="Calendar Management Simulation",
                description=(
                    "You are given a founder's calendar for next week with 15 meetings, "
                    "3 conflicts, and 2 timezone differences. Resolve conflicts, "
                    "send reschedule emails, and ensure 2-hour focus blocks daily."
                ),
                category="admin",
                difficulty="medium",
                estimated_hours=2.0,
                evaluation_criteria=[
                    "All conflicts resolved",
                    "Professional reschedule emails",
                    "Focus blocks preserved",
                    "Timezone handling correct",
                    "Clear communication",
                ],
            ),
            TrialTask(
                id="admin_email",
                title="Email Triage & Response",
                description=(
                    "Process 20 emails: categorize (urgent/action/fyi/archive), "
                    "draft responses for 5 requiring replies, flag 3 for founder review."
                ),
                category="admin",
                difficulty="easy",
                estimated_hours=1.5,
                evaluation_criteria=[
                    "Correct categorization",
                    "Professional response drafts",
                    "Appropriate escalation",
                    "Zero missed urgent items",
                ],
            ),
        ],
        "marketing": [
            TrialTask(
                id="marketing_social",
                title="Social Media Content Calendar",
                description=(
                    "Create a 2-week content calendar for a SaaS founder's LinkedIn/Twitter. "
                    "Include 10 posts: 3 educational, 3 personal, 2 promotional, 2 curated. "
                    "Write copy for all 10 posts."
                ),
                category="marketing",
                difficulty="medium",
                estimated_hours=3.0,
                evaluation_criteria=[
                    "Balanced content mix",
                    "Engaging hooks",
                    "Clear CTAs",
                    "Founder voice match",
                    "Hashtag strategy",
                ],
            ),
        ],
        "ecommerce": [
            TrialTask(
                id="ecommerce_shopify",
                title="Shopify Order Processing",
                description=(
                    "Process 15 orders: verify payment, check inventory, "
                    "print labels, send shipping confirmations, handle 2 returns."
                ),
                category="ecommerce",
                difficulty="easy",
                estimated_hours=2.0,
                evaluation_criteria=[
                    "All orders processed",
                    "Correct label generation",
                    "Timely customer communication",
                    "Return handling per policy",
                ],
            ),
        ],
        "operations": [
            TrialTask(
                id="ops_sop",
                title="SOP Creation",
                description=(
                    "Document the 'New Client Onboarding' process as an SOP. "
                    "Include: trigger, steps, owners, tools, templates, success criteria. "
                    "Format in Notion with checklist."
                ),
                category="operations",
                difficulty="medium",
                estimated_hours=3.0,
                evaluation_criteria=[
                    "Complete step coverage",
                    "Clear ownership",
                    "Tool integration",
                    "Template inclusion",
                    "Measurable success criteria",
                ],
            ),
        ],
        "sales": [
            TrialTask(
                id="sales_outreach",
                title="Cold Outreach Campaign",
                description=(
                    "Research 20 target prospects, find verified emails, "
                    "write 5 personalized cold email sequences (3 touches each), "
                    "set up in Instantly/Smartlead."
                ),
                category="sales",
                difficulty="hard",
                estimated_hours=4.0,
                evaluation_criteria=[
                    "Prospect quality/relevance",
                    "Email personalization",
                    "Sequence logic",
                    "Technical setup correct",
                    "Compliance (unsubscribe, CAN-SPAM)",
                ],
            ),
        ],
    }

    @classmethod
    def get_tasks(cls, category: str) -> list:
        return cls.TASKS.get(category, [])

    @classmethod
    def get_task(cls, task_id: str) -> Any:
        for tasks in cls.TASKS.values():
            for task in tasks:
                if task.id == task_id:
                    return task
        return None


class DefaultVettingWorkflow(VettingWorkflow):
    """Default implementation of VA vetting workflow."""

    def __init__(self):
        self.english_tests = EnglishTestBank()
        self.trial_tasks = TrialTaskBank()
        self.reference_checks: dict[str, list[ReferenceCheck]] = {}

    async def run_english_test(self, va_id: str, test_type: str = "standard") -> float:
        """Run English proficiency test (simulated)."""
        log.info(f"Running English test ({test_type}) for VA {va_id}")

        test = EnglishTestBank.get_test(test_type)
        # In production: send test link, collect answers, auto-grade
        # Simulate: random score around 0.7-0.95
        score = random.uniform(0.65, 0.95)

        log.info(f"English test result for {va_id}: {score:.2%}")
        return score

    async def run_trial_task(self, va_id: str, task_id: str) -> float:
        """Run trial task assessment (simulated)."""
        task = TrialTaskBank.get_task(task_id)
        if not task:
            log.warning(f"Trial task not found: {task_id}")
            return 0.0

        log.info(f"Running trial task {task_id} for VA {va_id}")

        # In production: assign task, collect deliverable, human/auto evaluation
        # Simulate: score based on task difficulty
        base_score = {"easy": 85, "medium": 75, "hard": 65}.get(
            getattr(task, "difficulty", "medium"), 75
        )
        score = random.uniform(base_score - 10, min(100, base_score + 10))

        log.info(f"Trial task {task_id} result for {va_id}: {score:.1f}")
        return score / 100.0  # Normalize to 0-1

    async def check_references(self, va_id: str, references: list[dict]) -> bool:
        """Check VA references."""
        log.info(f"Checking {len(references)} references for VA {va_id}")

        checks = []
        for ref in references:
            check = ReferenceCheck(
                reference_name=ref.get("name", ""),
                reference_email=ref.get("email", ""),
                relationship=ref.get("relationship", ""),
                years_known=ref.get("years_known", 0),
                rating=ref.get("rating", 0),
                strengths=ref.get("strengths", []),
                weaknesses=ref.get("weaknesses", []),
                would_rehire=ref.get("would_rehire", True),
                comments=ref.get("comments", ""),
                verified=True,  # In production: send email, verify response
            )
            checks.append(check)

        self.reference_checks[va_id] = checks

        # Pass if all ratings >= 4 and would_rehire all True
        passed = all(c.rating >= 4.0 and c.would_rehire for c in checks)
        log.info(f"Reference check for {va_id}: {'PASSED' if passed else 'FAILED'}")
        return passed

    async def calculate_vetting_score(self, va_id: str) -> float:
        """Calculate overall vetting score from components."""
        # In production: fetch stored test/task/reference results
        # Simulate aggregate score
        english_score = random.uniform(0.7, 0.95)
        trial_score = random.uniform(0.7, 0.95)
        reference_passed = True  # Would fetch from storage

        # Weighted: English 30%, Trial 50%, References 20% (pass/fail)
        score = (
            0.30 * english_score +
            0.50 * trial_score +
            0.20 * (1.0 if True else 0.0)
        )

        return round(score, 2)


class VettingService:
    """High-level vetting service orchestrating the full workflow."""

    def __init__(self):
        self.workflow = DefaultVettingWorkflow()
        self.va_status: dict[str, VAStatus] = {}

    async def vet_va(self, va: VAProfile, task_category: str = "admin") -> VAProfile:
        """Run complete vetting workflow for a VA."""
        log.info(f"Starting vetting for VA {va.id} ({va.full_name})")

        self.va_status[va.id] = VAStatus.VETTING
        va.status = VAStatus.VETTING

        # 1. English test
        english_score = await self.workflow.run_english_test(va.id, "standard")
        va.english_test_score = english_score

        if english_score < 0.75:
            va.status = VAStatus.REJECTED
            log.warning(f"VA {va.id} failed English test: {english_score:.2%}")
            return va

        # 2. Trial task
        tasks = TrialTaskBank.get_tasks(task_category)
        if tasks:
            task = tasks[0]  # Use first task for category
            trial_score = await self.workflow.run_trial_task(va.id, task.id)
            va.trial_task_score = trial_score

            if trial_score < 0.70:
                va.status = VAStatus.REJECTED
                log.warning(f"VA {va.id} failed trial task: {trial_score:.2%}")
                return va

        # 3. Reference check (would need references from VA profile)
        # In production: request references from VA, send email forms
        # For now, assume passed
        ref_passed = True
        va.reference_check_passed = ref_passed

        # 4. Calculate final vetting score
        vetting_score = await self.workflow.calculate_vetting_score(va.id)
        va.vetting_score = vetting_score

        if vetting_score >= 0.75:
            va.status = VAStatus.ACTIVE
            log.info(f"VA {va.id} PASSED vetting with score {vetting_score:.2f}")
        else:
            va.status = VAStatus.REJECTED
            log.warning(f"VA {va.id} REJECTED with score {vetting_score:.2f}")

        return va

    async def bulk_vet(self, vas: list, task_category: str = "admin") -> list:
        """Vet multiple VAs concurrently."""
        semaphore = asyncio.Semaphore(3)  # Limit concurrent vetting

        async def vet_one(va):
            async with semaphore:
                return await self.vet_va(va, task_category)

        results = await asyncio.gather(
            *[vet_one(va) for va in vas],
            return_exceptions=True
        )

        vetted = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Vetting failed for VA {vas[i].id}: {result}")
            else:
                vetted.append(result)

        return vetted


# Default SOP templates for onboarding
DEFAULT_SOPS = {
    "onboarding_client": {
        "name": "Client Onboarding SOP",
        "category": "onboarding",
        "variables": ["client_name", "va_name", "start_date", "tools_list", "communication_channels"],
        "content": """# Client Onboarding SOP

## Client: {{client_name}}
## VA: {{va_name}}
## Start Date: {{start_date}}

### 1. Access Setup
- [ ] Grant access to: {{tools_list}}
- [ ] Set up shared password manager (1Password/LastPass)
- [ ] Configure email delegation (if applicable)

### 2. Communication Setup
- [ ] Primary channel: {{communication_channels[0]}}
- [ ] Emergency: {{communication_channels[1] if communication_channels|length > 1 else 'N/A'}}
- [ ] Weekly sync: {{communication_channels[2] if communication_channels|length > 2 else 'Friday 10 AM'}}

### 3. First Week Checklist
- [ ] Day 1: Access verification, intro calls
- [ ] Day 2: Shadow current processes
- [ ] Day 3: Begin task ownership
- [ ] Day 4: First deliverable review
- [ ] Day 5: Week 1 retro

### 4. Ongoing Cadence
- Daily: Async update in {{communication_channels[0]}}
- Weekly: 30-min sync call
- Monthly: 60-min strategic review
""",
    },
    "onboarding_va": {
        "name": "VA Onboarding SOP",
        "category": "onboarding",
        "variables": ["va_name", "client_name", "tools_list", "sop_list", "contact_info"],
        "content": """# VA Onboarding SOP

## VA: {{va_name}}
## Client: {{client_name}}

### 1. System Access
- [ ] {{tools_list}} - granted by {{client_name}}
- [ ] Password manager access
- [ ] Email/calendar delegation

### 2. SOPs to Review
{{sop_list}}

### 3. Communication Protocols
- Primary: {{contact_info.primary}}
- Emergency: {{contact_info.emergency}}
- Weekly sync: {{contact_info.weekly_sync}}

### 4. First 30 Days Milestones
- Week 1: Access + shadowing
- Week 2: First independent tasks
- Week 3: Full task ownership
- Week 4: 30-day review
""",
    },
    "communication": {
        "name": "Communication Protocol SOP",
        "category": "communication",
        "variables": ["client_name", "va_name", "response_time_hours", "escalation_path"],
        "content": """# Communication Protocol

## {{client_name}} <-> {{va_name}}

### Response Time Expectations
- Urgent ({{escalation_path.urgent}}): {{response_time_hours.urgent}} hours
- High ({{escalation_path.high}}): {{response_time_hours.high}} hours
- Normal: {{response_time_hours.normal}} hours
- FYI: No response needed

### Channels
- {{channels}}

### Escalation Path
1. {{escalation_path.level1}}
2. {{escalation_path.level2}}
3. {{escalation_path.level3}}

### Meeting Cadence
- Daily async update: {{meeting_cadence.daily}}
- Weekly sync: {{meeting_cadence.weekly}}
- Monthly review: {{meeting_cadence.monthly}}
""",
    },
    "task_management": {
        "name": "Task Management SOP",
        "category": "task_management",
        "variables": ["client_name", "va_name", "task_tool", "priority_labels", "reporting_cadence"],
        "content": """# Task Management SOP

## {{client_name}} <-> {{va_name}}

### Task Tool: {{task_tool}}

### Priority Labels
{{priority_labels}}

### Workflow
1. Client adds task → {{priority_labels.urgent}}/{{priority_labels.high}}/{{priority_labels.normal}}
2. VA acknowledges within {{acknowledge_time}}
3. VA updates status: To Do → In Progress → Review → Done
4. Client reviews → Approves/Requests changes

### Reporting
- {{reporting_cadence}}: Summary of completed/in-progress/blocked
- Monthly: Time tracking report + recommendations
""",
    },
}