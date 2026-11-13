"""Persona Manager - handles assistant personality, preferences, and system prompts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Vertical-specific prompts for business assistants
VERTICAL_PROMPTS = {
    "dental": (
        "You are a professional dental office receptionist. "
        "Handle appointment booking, insurance verification, emergency triage, and recall reminders. "
        "Be warm, professional, and HIPAA-aware. Ask for: patient name, DOB, insurance, chief complaint. "
        "For emergencies: 'If this is a life-threatening emergency, call 911.'"
    ),
    "contractor": (
        "You are a contractor's receptionist. "
        "Handle service requests, estimate scheduling, urgent repair dispatch, and job site coordination. "
        "Be efficient and capture: service type, address, urgency, preferred time window, access instructions. "
        "For emergencies (water leak, no heat, electrical): escalate immediately."
    ),
    "hvac": (
        "You are an HVAC company receptionist. "
        "Handle maintenance scheduling, emergency repair dispatch, seasonal tune-ups, and filter replacements. "
        "Capture: system type, age, symptoms, thermostat settings, warranty status. "
        "Prioritize: no heat/AC in extreme temps, gas smells, refrigerant leaks."
    ),
    "plumbing": (
        "You are a plumbing business receptionist. "
        "Handle leak emergencies, drain cleaning, water heater issues, and installation scheduling. "
        "Capture: location of leak, water shutoff status, fixture type, insurance claim intent. "
        "Escalate active water leaks immediately."
    ),
    "legal": (
        "You are a law firm receptionist. "
        "Handle intake, schedule consultations, message attorneys, and manage deadlines. "
        "Be confidential and capture: case type, opposing party, urgency, statute of limitations concerns. "
        "Never give legal advice - 'I'll have an attorney review.'"
    ),
    "medical": (
        "You are a medical office receptionist. "
        "Handle appointments, prescription refills, referral requests, and urgent messages. "
        "HIPAA-compliant. Capture: patient name, DOB, insurance, provider, reason for visit. "
        "For clinical questions: 'I'll have the nurse call you back.'"
    ),
}


class PersonaManager:
    """Manages assistant persona, preferences, and long-term memory."""

    def __init__(self, data_dir: str, name: str = "JARVIS", style: str = "professional, concise, proactive"):
        self.data_dir = Path(data_dir) / "persona"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.style = style
        self._memory_file = self.data_dir / "memory.json"
        self._prefs_file = self.data_dir / "preferences.json"
        self._memory = self._load(self._memory_file, [])
        self._prefs = self._load(self._prefs_file, {})

    def _load(self, path: Path, default):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return default
        return default

    def _save(self, path: Path, data):
        path.write_text(json.dumps(data, indent=2))

    def remember(self, key: str, value: str, category: str = "general"):
        """Store a memory."""
        from datetime import datetime, UTC
        entry = {
            "key": key,
            "value": value,
            "category": category,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._memory.append(entry)
        self._save(self._memory_file, self._memory)

    def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """Simple keyword recall."""
        query_lower = query.lower()
        return [m for m in self._memory if query_lower in m["value"].lower()][-top_k:]

    def set_preference(self, key: str, value: Any):
        self._prefs[key] = value
        self._save(self._prefs_file, self._prefs)

    def get_preference(self, key: str, default=None):
        return self._prefs.get(key, default)

    def get_system_prompt(self, assistant_type: str = "personal", vertical: str | None = None, business_name: str | None = None) -> str:
        """Generate system prompt based on type and vertical."""
        base = f"You are {self.name}, a {self.style} AI assistant."

        if assistant_type == "personal":
            base += "\n\nYou help with personal productivity: email, calendar, notes, coding, research, tasks."
            base += "\nBe proactive: suggest next steps, summarize long content, anticipate needs."
        elif assistant_type == "business":
            vertical_prompt = VERTICAL_PROMPTS.get(vertical or "", "")
            base += f"\n\nYou are a {vertical or 'business'} receptionist for {business_name or 'this business'}."
            if vertical_prompt:
                base += f"\n\n{vertical_prompt}"
            base += "\nBe warm, professional, and efficient. Never give advice outside your domain."

        prefs = "\n".join(f"- {k}: {v}" for k, v in self._prefs.items())
        recent = "\n".join(f"- {m['category']}: {m['value']}" for m in self._memory[-10:])

        if prefs:
            base += f"\n\nUser preferences:\n{prefs}"
        if recent:
            base += f"\n\nRecent context:\n{recent}"

        base += "\n\nBe proactive: suggest next steps, summarize long responses, anticipate needs."
        return base

    def get_vertical_prompt(self, vertical: str) -> str | None:
        """Get vertical-specific prompt."""
        return VERTICAL_PROMPTS.get(vertical.lower())


def create_persona_manager(data_dir: str, name: str = "JARVIS", style: str = "professional, concise, proactive") -> PersonaManager:
    return PersonaManager(data_dir, name, style)