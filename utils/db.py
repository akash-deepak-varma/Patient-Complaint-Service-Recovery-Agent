"""
utils/db.py — Patient history database helpers (mock JSON store).

register_complaint(context):
    Persists a processed complaint into data/mock_patient_history.json.
    - If the patient already exists, appends the new case to their prior_cases
      and adds the appointment_id (if any) to their appointment_ids list.
    - If the patient is new, creates a fresh record for them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from models.complaint_context import ComplaintContext

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_patient_history.json")


def _load() -> dict:
    with open(_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_complaint(context: ComplaintContext) -> None:
    """
    Write the processed complaint into the patient history database.

    Creates a new patient record if none exists, or appends to an
    existing record matched by patient_name (case-insensitive) or
    appointment_id.
    """
    db = _load()
    patients: list[dict] = db.setdefault("patients", [])

    # Build the new case entry string
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    category = context.category.value if context.category else "OTHER"
    summary = context.summary or context.raw_email[:120].replace("\n", " ")
    escalation = context.escalation_level.value
    status = context.resolution_status.value
    new_case = (
        f"{date_str}: [{category}] {summary} "
        f"(Escalation: {escalation}, Status: {status}, "
        f"Ref: {context.complaint_id[:8]})"
    )

    # Try to find an existing record
    patient_name_lower = (context.patient_name or "").lower().strip()
    appt_id = context.appointment_id

    matched_record: dict | None = None
    for record in patients:
        name_match = patient_name_lower and record["patient_name"].lower() == patient_name_lower
        appt_match = appt_id and appt_id in record.get("appointment_ids", [])
        if name_match or appt_match:
            matched_record = record
            break

    if matched_record:
        # Append new case
        matched_record["prior_cases"].append(new_case)
        # Add appointment_id if new
        if appt_id and appt_id not in matched_record.get("appointment_ids", []):
            matched_record.setdefault("appointment_ids", []).append(appt_id)
    else:
        # Create a new patient record
        new_record = {
            "patient_name": context.patient_name or "Unknown Patient",
            "appointment_ids": [appt_id] if appt_id else [],
            "prior_cases": [new_case],
        }
        patients.append(new_record)

    _save(db)
