"""
Extraction Agent — extracts structured entities from the complaint email.
Entities: patient name, appointment ID, department, service date, staff references.
"""

import json
import os

from openai import OpenAI

from models.complaint_context import ComplaintContext

_SYSTEM_PROMPT = """You are an information extraction assistant for a healthcare complaint system.
Given a patient complaint email, extract the following fields if present:
- patient_name: Full name of the patient (string or null)
- appointment_id: Any appointment, visit, or reference ID mentioned (string or null)
- department: Hospital department or clinic mentioned (string or null)
- service_date: Date of the service or visit mentioned (string in any format, or null)
- staff_references: List of staff names or roles mentioned (list of strings, empty list if none)

Respond ONLY with valid JSON matching this structure exactly:
{
  "patient_name": "...",
  "appointment_id": "...",
  "department": "...",
  "service_date": "...",
  "staff_references": ["..."]
}
Use null for fields that are not present in the email.
"""


def run(context: ComplaintContext) -> ComplaintContext:
    """Extract entities from the raw email and write them onto the context."""
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    response = client.chat.completions.create(
        model="gpt-5.6-sol",
        temperature=1,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": context.raw_email},
        ],
    )
    raw = response.choices[0].message.content.strip()
    data = json.loads(raw)

    context.patient_name = data.get("patient_name")
    context.appointment_id = data.get("appointment_id")
    context.department = data.get("department")
    context.service_date = data.get("service_date")
    context.staff_references = data.get("staff_references") or []
    return context
