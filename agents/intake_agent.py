"""
Intake Agent — classifies the complaint category and produces a one-sentence summary.
Uses the OpenAI API (gpt-3.5-turbo). API key read from OPENAI_API_KEY env var.
"""

import json
import os

from openai import OpenAI

from models.complaint_context import ComplaintCategory, ComplaintContext

_SYSTEM_PROMPT = """You are a healthcare complaint triage assistant.
Given a patient complaint email, do two things:
1. Classify the complaint into exactly ONE of these categories:
   BILLING, SCHEDULING, STAFF_BEHAVIOUR, FACILITY, CLINICAL_QUALITY, OTHER
2. Write a single sentence (max 25 words) summarising the core issue.

Respond ONLY with valid JSON in this exact format:
{"category": "<CATEGORY>", "summary": "<one-sentence summary>"}
"""


def run(context: ComplaintContext) -> ComplaintContext:
    """Classify the complaint and write category + summary onto the context."""
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

    category_str = data.get("category", "OTHER").upper()
    context.category = ComplaintCategory(category_str) if category_str in ComplaintCategory._value2member_map_ else ComplaintCategory.OTHER
    context.summary = data.get("summary", "")
    return context
