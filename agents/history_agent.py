"""
History Agent — retrieves prior complaint cases and interaction notes for a patient.
Data source: data/mock_patient_history.json (mock fixture).
"""

import json
import os
from typing import List

from models.complaint_context import ComplaintContext

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_patient_history.json")


def _load_history() -> list:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["patients"]


def _find_patient(records: list, patient_name: str | None, appointment_id: str | None) -> List[str]:
    """Return prior cases for the first matching patient record."""
    for record in records:
        name_match = patient_name and record["patient_name"].lower() == patient_name.lower()
        appt_match = appointment_id and appointment_id in record["appointment_ids"]
        if name_match or appt_match:
            return record["prior_cases"]
    return []


def run(context: ComplaintContext) -> ComplaintContext:
    """Look up patient history and write it onto the context."""
    records = _load_history()
    context.case_history = _find_patient(records, context.patient_name, context.appointment_id)
    return context
