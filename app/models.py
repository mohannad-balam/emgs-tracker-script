from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PassportTarget:
    passport_number: str
    destination_email: str


@dataclass
class HistoryItem:
    date: str
    status: str
    remark: str


@dataclass
class VisaSnapshot:
    percentage: Optional[int] = None
    percentage_color: Optional[str] = None
    percentage_color_label: Optional[str] = None
    percentage_color_meaning: Optional[str] = None
    full_name: Optional[str] = None
    travel_document_number: Optional[str] = None
    application_number: Optional[str] = None
    application_type: Optional[str] = None
    application_status: Optional[str] = None
    explanation: Optional[str] = None
    history: List[HistoryItem] = field(default_factory=list)

    def stable_fingerprint(self) -> Dict[str, Any]:
        return {
            "percentage": self.percentage,
            "percentage_color": self.percentage_color,
            "application_status": self.application_status,
            "application_number": self.application_number,
            "history_top": asdict(self.history[0]) if self.history else None,
        }


@dataclass
class TemporaryIssue:
    title: str
    detail: str
    technical_detail: Optional[str] = None


class ConfigError(Exception):
    pass


class TrackerError(Exception):
    pass


class TemporaryExternalServiceError(TrackerError):
    """Used for EMGS/vendor backend outages and temporary connectivity failures."""


class UnexpectedResponseError(TrackerError):
    """Used when the page returned is not a valid status page."""