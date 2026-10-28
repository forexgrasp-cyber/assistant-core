"""
Base email sender interface and result types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class SendResult:
    """Result of sending a single email."""
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    recipient: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchSendResult:
    """Result of sending a batch of emails."""
    total: int
    successful: int
    failed: int
    results: List[SendResult]


class EmailSender(ABC):
    """Abstract base class for email senders."""

    provider_name: str = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def send(
        self,
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Send a single email."""
        pass

    @abstractmethod
    async def send_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> BatchSendResult:
        """Send multiple emails efficiently."""
        pass

    @abstractmethod
    async def verify_domain(self, domain: str) -> bool:
        """Verify domain is configured for sending."""
        pass

    @abstractmethod
    async def get_sending_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get sending statistics for a date range."""
        pass

    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process incoming webhook from provider (bounces, complaints, etc.)."""
        pass

    def normalize_email(self, email: str, name: Optional[str] = None) -> str:
        """Format email address with optional name."""
        if name:
            return f"{name} <{email}>"
        return email