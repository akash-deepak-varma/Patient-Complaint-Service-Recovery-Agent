"""
Shared data schema for the Patient Complaint & Service Recovery Agent pipeline.
All agents read from and write to a single ComplaintContext instance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    """Lifecycle states of a complaint."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class EscalationLevel(str, Enum):
    """Severity of escalation required."""
    NONE = "NONE"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ComplaintCategory(str, Enum):
    """Top-level categories a complaint can be classified into."""
    BILLING = "BILLING"
    SCHEDULING = "SCHEDULING"
    STAFF_BEHAVIOUR = "STAFF_BEHAVIOUR"
    FACILITY = "FACILITY"
    CLINICAL_QUALITY = "CLINICAL_QUALITY"
    OTHER = "OTHER"


class AuditEntry(BaseModel):
    """A single timestamped entry in the complaint audit log."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: str


class ComplaintContext(BaseModel):
    """
    Central state object passed through the entire agent pipeline.
    Each agent populates the fields relevant to its responsibility.
    """

    # --- Identity ---
    complaint_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this complaint.",
    )

    # --- Input ---
    raw_email: str = Field(
        default="",
        description="The full text of the inbound complaint email.",
    )

    # --- Intake Agent outputs ---
    category: Optional[ComplaintCategory] = Field(
        default=None,
        description="Complaint category assigned by the Intake Agent.",
    )
    summary: Optional[str] = Field(
        default=None,
        description="One-sentence summary of the complaint.",
    )

    # --- Extraction Agent outputs ---
    patient_name: Optional[str] = Field(default=None, description="Patient's full name.")
    appointment_id: Optional[str] = Field(default=None, description="Appointment or visit ID.")
    department: Optional[str] = Field(default=None, description="Hospital department referenced.")
    service_date: Optional[str] = Field(default=None, description="Date of the service in question.")
    staff_references: List[str] = Field(
        default_factory=list,
        description="Names or roles of staff mentioned in the complaint.",
    )

    # --- History Agent outputs ---
    case_history: List[str] = Field(
        default_factory=list,
        description="Prior complaint summaries retrieved for this patient.",
    )

    # --- Routing Agent outputs ---
    assigned_department: Optional[str] = Field(
        default=None,
        description="Department the complaint has been routed to.",
    )
    escalation_level: EscalationLevel = Field(
        default=EscalationLevel.NONE,
        description="Escalation severity determined by the Routing Agent.",
    )
    escalation_reasoning: Optional[str] = Field(
        default=None,
        description="LLM explanation for the escalation decision.",
    )

    # --- Response Agent outputs ---
    response_draft: Optional[str] = Field(
        default=None,
        description="Draft reply email produced by the Response Agent.",
    )

    # --- Tracker Agent outputs ---
    resolution_status: ResolutionStatus = Field(
        default=ResolutionStatus.OPEN,
        description="Current lifecycle status of the complaint.",
    )
    audit_log: List[AuditEntry] = Field(
        default_factory=list,
        description="Timestamped log of all status changes and key events.",
    )
