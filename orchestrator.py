"""
Orchestrator — wires all agents into a single end-to-end complaint processing pipeline.

Usage:
    from orchestrator import run_pipeline
    context = run_pipeline(raw_email)

CLI:
    python orchestrator.py
"""

import logging

from models.complaint_context import ComplaintContext, ResolutionStatus
from agents import intake_agent, extraction_agent, history_agent, routing_agent, response_agent, tracker_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def run_pipeline(raw_email: str) -> ComplaintContext:
    """
    Run the full complaint-processing pipeline on the given email text.

    Pipeline order:
        1. Intake Agent      — categorize + summarize
        2. Extraction Agent  — extract entities
        3. History Agent     — retrieve case history
        4. Routing Agent     — assign department + escalation level
        5. Response Agent    — draft empathetic reply
        6. Tracker Agent     — set status to IN_PROGRESS

    Returns a fully populated ComplaintContext.
    """
    context = ComplaintContext(raw_email=raw_email)
    log.info("Pipeline started — complaint_id=%s", context.complaint_id)

    # 1. Intake
    context = intake_agent.run(context)
    log.info("Intake Agent — category=%s, summary=%s", context.category, context.summary)

    # 2. Extraction
    context = extraction_agent.run(context)
    log.info(
        "Extraction Agent — patient=%s, appt=%s, dept=%s, date=%s, staff=%s",
        context.patient_name, context.appointment_id,
        context.department, context.service_date, context.staff_references,
    )

    # 3. History
    context = history_agent.run(context)
    log.info("History Agent — %d prior case(s) found", len(context.case_history))

    # 4. Routing
    context = routing_agent.run(context)
    log.info(
        "Routing Agent — assigned_dept=%s, escalation=%s",
        context.assigned_department, context.escalation_level,
    )

    # 5. Response
    context = response_agent.run(context)
    log.info("Response Agent — draft generated (%d chars)", len(context.response_draft or ""))

    # 6. Tracker — set initial pipeline status
    context = tracker_agent.run(context, ResolutionStatus.IN_PROGRESS)
    log.info("Tracker Agent — status=%s", context.resolution_status)

    log.info("Pipeline complete — complaint_id=%s", context.complaint_id)
    return context


if __name__ == "__main__":
    SAMPLE_EMAIL = """
    Dear Hospital,

    I am writing to express my deep dissatisfaction with the billing I received following
    my visit on 15th July 2024. My appointment ID is APT-1001 and I am John Smith.
    I was charged for procedures that were never performed. This is unacceptable and I
    expect an immediate correction to my invoice.

    Regards,
    John Smith
    """

    result = run_pipeline(SAMPLE_EMAIL)

    print("\n" + "=" * 60)
    print("PIPELINE RESULT")
    print("=" * 60)
    print(f"Complaint ID   : {result.complaint_id}")
    print(f"Category       : {result.category}")
    print(f"Summary        : {result.summary}")
    print(f"Patient        : {result.patient_name}")
    print(f"Appointment    : {result.appointment_id}")
    print(f"Department     : {result.department}")
    print(f"Service Date   : {result.service_date}")
    print(f"Staff Refs     : {result.staff_references}")
    print(f"Prior Cases    : {len(result.case_history)}")
    print(f"Routed To      : {result.assigned_department}")
    print(f"Escalation     : {result.escalation_level}")
    print(f"Status         : {result.resolution_status}")
    print(f"\nDRAFT RESPONSE:\n{result.response_draft}")
    print(f"\nAUDIT LOG:")
    for entry in result.audit_log:
        print(f"  [{entry.timestamp}] {entry.message}")
