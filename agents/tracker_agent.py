"""
Tracker Agent — manages the complaint lifecycle with validated status transitions
and a timestamped audit log.
"""

from models.complaint_context import AuditEntry, ComplaintContext, ResolutionStatus

# Valid status transitions: current → set of allowed next statuses
_VALID_TRANSITIONS: dict[ResolutionStatus, set[ResolutionStatus]] = {
    ResolutionStatus.OPEN: {ResolutionStatus.IN_PROGRESS, ResolutionStatus.ESCALATED},
    ResolutionStatus.IN_PROGRESS: {ResolutionStatus.RESOLVED, ResolutionStatus.ESCALATED},
    ResolutionStatus.ESCALATED: {ResolutionStatus.IN_PROGRESS, ResolutionStatus.RESOLVED},
    ResolutionStatus.RESOLVED: set(),  # terminal state
}


def update_status(context: ComplaintContext, new_status: ResolutionStatus) -> ComplaintContext:
    """
    Transition the complaint to a new resolution status.

    Raises ValueError for invalid transitions (e.g. RESOLVED → OPEN).
    Appends a timestamped entry to the audit log on every successful change.
    """
    current = context.resolution_status
    allowed = _VALID_TRANSITIONS.get(current, set())

    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition: {current.value} → {new_status.value}. "
            f"Allowed transitions from {current.value}: "
            f"{[s.value for s in allowed] or 'none (terminal state)'}."
        )

    context.resolution_status = new_status
    context.audit_log.append(
        AuditEntry(message=f"Status changed from {current.value} to {new_status.value}.")
    )
    return context


def run(context: ComplaintContext, new_status: ResolutionStatus = ResolutionStatus.IN_PROGRESS) -> ComplaintContext:
    """Set the initial pipeline status. Defaults to IN_PROGRESS."""
    return update_status(context, new_status)
