"""
Routing Agent — uses an LLM to decide the responsible department and escalation level.

The agent is given the full complaint context (email, category, summary, case history)
and asked to reason holistically about:
  - Which department should handle this complaint
  - What escalation level is appropriate (NONE / LOW / HIGH / CRITICAL)

This replaces the previous keyword-based approach with genuine LLM reasoning,
which handles nuance, tone, implicit threats, and pattern recognition across
case history that simple keyword matching cannot.
"""

import json
import os

from openai import OpenAI

from models.complaint_context import (
    ComplaintCategory,
    ComplaintContext,
    EscalationLevel,
)

# --- Department reference provided to the LLM so it uses consistent names ---
_DEPARTMENT_MAP = {
    "BILLING": "Finance & Billing Department",
    "SCHEDULING": "Patient Scheduling Office",
    "STAFF_BEHAVIOUR": "Human Resources & Patient Relations",
    "FACILITY": "Facilities Management",
    "CLINICAL_QUALITY": "Clinical Governance & Quality",
    "OTHER": "Patient Services",
}

_SYSTEM_PROMPT = """You are a senior healthcare complaint routing specialist.
Given a patient complaint, you must decide:
1. Which department should handle it (assigned_department).
2. The escalation level (escalation_level): NONE, LOW, HIGH, or CRITICAL.

Use the following department reference:
- Finance & Billing Department           → billing, invoicing, overcharging
- Patient Scheduling Office              → appointment booking, cancellations, wait times
- Human Resources & Patient Relations    → staff conduct, rudeness, discrimination
- Facilities Management                  → cleanliness, equipment, environment
- Clinical Governance & Quality          → medical errors, wrong treatment, patient safety
- Patient Services                       → general feedback, parking, signage, other

Escalation guidelines (reason carefully, do not rely on exact keywords):
- NONE      → Routine complaint, no safety or legal implications, first occurrence
- LOW       → Repeat complainant (2+ prior cases), or moderately serious concern
- HIGH      → Explicit mention of legal action, professional misconduct, serious distress,
               or multiple prior unresolved issues
- CRITICAL  → Patient safety incident (wrong medication, injury, death, life-threatening
               situation), or imminent legal/regulatory action

Respond ONLY with valid JSON in this exact format:
{
  "assigned_department": "<department name from the reference list>",
  "escalation_level": "<NONE|LOW|HIGH|CRITICAL>",
  "reasoning": "<1-2 sentence explanation of your escalation decision>"
}
"""


def _build_prompt(context: ComplaintContext) -> str:
    parts = [
        f"Complaint Category: {context.category.value if context.category else 'OTHER'}",
        f"Summary: {context.summary or '(no summary)'}",
        f"Prior Cases ({len(context.case_history)} found):",
    ]
    if context.case_history:
        for case in context.case_history:
            parts.append(f"  - {case}")
    else:
        parts.append("  - None")
    parts.append(f"\nFull Complaint Email:\n{context.raw_email}")
    return "\n".join(parts)


def run(context: ComplaintContext) -> ComplaintContext:
    """
    Call the LLM to determine the assigned department and escalation level.
    Falls back to rule-based defaults if the LLM response cannot be parsed.
    """
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )

    response = client.chat.completions.create(
        model="gpt-5.6-sol",
        temperature=1,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(context)},
        ],
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
        department = data.get("assigned_department", "").strip()
        escalation_str = data.get("escalation_level", "NONE").upper()

        # Validate escalation value
        escalation = (
            EscalationLevel(escalation_str)
            if escalation_str in EscalationLevel._value2member_map_
            else EscalationLevel.NONE
        )

        # Validate department — fall back to category-based default if unrecognised
        valid_departments = set(_DEPARTMENT_MAP.values())
        if department not in valid_departments:
            category = context.category or ComplaintCategory.OTHER
            department = _DEPARTMENT_MAP.get(category.value, "Patient Services")

        context.assigned_department = department
        context.escalation_level = escalation
        context.escalation_reasoning = data.get("reasoning")

    except (json.JSONDecodeError, ValueError):
        # Graceful fallback: use category-based department, NONE escalation
        category = context.category or ComplaintCategory.OTHER
        context.assigned_department = _DEPARTMENT_MAP.get(category.value, "Patient Services")
        context.escalation_level = EscalationLevel.NONE

    return context
