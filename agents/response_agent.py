"""
Response Agent — drafts an empathetic reply email to the patient.
Tone is adjusted based on escalation level. Uses the OpenAI API (gpt-3.5-turbo).
"""

import os

from openai import OpenAI

from models.complaint_context import ComplaintContext, EscalationLevel

_BASE_SYSTEM_PROMPT = """You are a compassionate patient relations officer at a hospital.
Your task is to write a professional, empathetic reply email to a patient who has submitted a complaint.

Guidelines:
- Address the patient by name.
- Acknowledge the complaint and thank them for bringing it to your attention.
- State which department will be handling their case.
- Give a realistic follow-up timeframe (within 3–5 business days for standard; within 24 hours for escalated).
- Use warm, professional language. Never be dismissive.
- Do NOT include placeholders — write a complete, ready-to-send email.
- Sign off as "Patient Relations Team, [Hospital Name]".
"""

_ESCALATION_ADDENDUM = """
This complaint has been flagged as high priority or critical. In addition to the standard guidelines:
- Open with a sincere, specific apology for the experience.
- Express that this matter is being treated with the utmost urgency.
- Assure the patient that senior leadership has been informed.
- Provide a 24-hour follow-up commitment.
"""


def _build_prompt(context: ComplaintContext) -> str:
    escalated = context.escalation_level in (EscalationLevel.HIGH, EscalationLevel.CRITICAL)
    parts = [
        f"Patient Name: {context.patient_name or 'Valued Patient'}",
        f"Complaint Summary: {context.summary or context.raw_email[:200]}",
        f"Assigned Department: {context.assigned_department or 'Patient Services'}",
        f"Escalation Level: {context.escalation_level.value}",
    ]
    if escalated:
        parts.append("Note: This is an escalated complaint — apply urgent, senior-level tone.")
    return "\n".join(parts)


def run(context: ComplaintContext) -> ComplaintContext:
    """Generate the draft response email and write it onto the context."""
    escalated = context.escalation_level in (EscalationLevel.HIGH, EscalationLevel.CRITICAL)
    system_prompt = _BASE_SYSTEM_PROMPT + (_ESCALATION_ADDENDUM if escalated else "")
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    response = client.chat.completions.create(
        model="gpt-5.6-sol",
        temperature=1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _build_prompt(context)},
        ],
    )
    context.response_draft = response.choices[0].message.content.strip()
    return context
