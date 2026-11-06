"""
Streamlit Operator Dashboard — Patient Complaint & Service Recovery Agent.
Run with: streamlit run app.py
"""

import streamlit as st

from models.complaint_context import EscalationLevel, ResolutionStatus
from orchestrator import run_pipeline
from utils.db import register_complaint

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Patient Complaint & Service Recovery Agent",
    page_icon="🏥",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏥 About This System")
    st.markdown(
        """
        This dashboard runs a **multi-agent complaint processing pipeline** on any
        patient complaint email you provide.

        **Pipeline stages:**
        1. 🗂️ Intake Agent — categorizes the complaint
        2. 🔍 Extraction Agent — extracts patient & appointment details
        3. 📁 History Agent — retrieves prior cases
        4. 🏥 Routing Agent — assigns department & escalation level
        5. ✉️ Response Agent — drafts an empathetic reply
        6. 📋 Tracker Agent — sets status to IN_PROGRESS

        **How to use:**
        1. Paste a complaint email in the text area on the right.
        2. Click **Run Pipeline**.
        3. Review all outputs below the input area.
        """
    )
    st.divider()
    st.caption("Powered by OpenAI gpt-5.6-sol")

# ── Escalation colour helpers ─────────────────────────────────────────────────
_ESCALATION_COLOUR = {
    EscalationLevel.NONE: "🟢",
    EscalationLevel.LOW: "🟡",
    EscalationLevel.HIGH: "🟠",
    EscalationLevel.CRITICAL: "🔴",
}

_STATUS_COLOUR = {
    ResolutionStatus.OPEN: "🔵",
    ResolutionStatus.IN_PROGRESS: "🟡",
    ResolutionStatus.RESOLVED: "🟢",
    ResolutionStatus.ESCALATED: "🔴",
}

# ── Custom CSS — smaller metric values ───────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        color: #57606a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Main page ─────────────────────────────────────────────────────────────────
st.title("🏥 Patient Complaint Management Centre")
st.caption("Triage · Route · Respond · Track — all incoming patient complaints in one place.")

st.divider()

# Input area
complaint_email = st.text_area(
    label="📧 Paste the patient complaint email here",
    height=200,
    placeholder=(
        "Dear Hospital,\n\n"
        "I am writing to complain about the long wait time during my appointment on 10th July 2024. "
        "My name is John Smith and my appointment ID is APT-1001. "
        "I waited over 3 hours without any update from staff...\n\n"
        "Regards,\nJohn Smith"
    ),
)

run_button = st.button("▶ Run Pipeline", type="primary", use_container_width=True)

# ── Run pipeline on button click ──────────────────────────────────────────────
if run_button:
    if not complaint_email.strip():
        st.warning("Please paste a complaint email before running the pipeline.")
    else:
        with st.spinner("Running agent pipeline…"):
            try:
                result = run_pipeline(complaint_email)
                register_complaint(result)
                st.session_state["result"] = result
                st.session_state["registered"] = True
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")
                st.stop()

if st.session_state.get("registered"):
    st.success("✅ Complaint registered in the patient database.")
    st.session_state["registered"] = False

# ── Display results ───────────────────────────────────────────────────────────
if "result" in st.session_state:
    ctx = st.session_state["result"]
    st.divider()
    st.subheader("📋 Complaint Case Overview")

    # --- Row 1: Summary + Status badges ---
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.metric("Complaint ID", ctx.complaint_id[:8] + "…")
    with col2:
        esc_icon = _ESCALATION_COLOUR.get(ctx.escalation_level, "⚪")
        st.metric("Escalation", f"{esc_icon} {ctx.escalation_level.value}")
    with col3:
        sta_icon = _STATUS_COLOUR.get(ctx.resolution_status, "⚪")
        st.metric("Status", f"{sta_icon} {ctx.resolution_status.value}")

    st.divider()

    # --- Section 1: Complaint Summary ---
    with st.expander("🗂️ Complaint Summary", expanded=True):
        st.markdown(f"**Category:** `{ctx.category.value if ctx.category else 'N/A'}`")
        st.markdown(f"**Summary:** {ctx.summary or '_No summary generated._'}")

    # --- Section 2: Extracted Details ---
    with st.expander("🔍 Extracted Details", expanded=True):
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown(f"**Patient Name:** {ctx.patient_name or '_Not found_'}")
            st.markdown(f"**Appointment ID:** {ctx.appointment_id or '_Not found_'}")
            st.markdown(f"**Department Mentioned:** {ctx.department or '_Not found_'}")
        with detail_col2:
            st.markdown(f"**Service Date:** {ctx.service_date or '_Not found_'}")
            staff = ", ".join(ctx.staff_references) if ctx.staff_references else "_None mentioned_"
            st.markdown(f"**Staff References:** {staff}")

    # --- Section 3: Case History ---
    with st.expander("📁 Case History", expanded=False):
        if ctx.case_history:
            for i, case in enumerate(ctx.case_history, 1):
                st.markdown(f"{i}. {case}")
        else:
            st.info("No prior complaint history found for this patient.")

    # --- Section 4: Routing Decision ---
    with st.expander("🏥 Routing Decision", expanded=True):
        routing_col1, routing_col2 = st.columns(2)
        with routing_col1:
            st.markdown(f"**Assigned Department:** {ctx.assigned_department or '_Not assigned_'}")
        with routing_col2:
            esc_icon = _ESCALATION_COLOUR.get(ctx.escalation_level, "⚪")
            level = ctx.escalation_level.value
            if ctx.escalation_level == EscalationLevel.CRITICAL:
                st.error(f"{esc_icon} Escalation Level: **{level}** — Immediate action required.")
            elif ctx.escalation_level == EscalationLevel.HIGH:
                st.warning(f"{esc_icon} Escalation Level: **{level}** — Urgent attention needed.")
            elif ctx.escalation_level == EscalationLevel.LOW:
                st.warning(f"{esc_icon} Escalation Level: **{level}** — Monitor closely.")
            else:
                st.success(f"{esc_icon} Escalation Level: **{level}** — Standard handling.")
        if ctx.escalation_reasoning:
            st.caption(f"🤖 Agent reasoning: {ctx.escalation_reasoning}")

    # --- Section 5: Draft Response ---
    with st.expander("✉️ Draft Response", expanded=True):
        st.caption("You may edit this draft before sending.")
        edited_draft = st.text_area(
            label="Draft response email",
            value=ctx.response_draft or "",
            height=300,
            label_visibility="collapsed",
        )

    # --- Section 6: Audit Log ---
    with st.expander("📋 Audit Log", expanded=False):
        if ctx.audit_log:
            log_data = [
                {"Timestamp (UTC)": entry.timestamp, "Event": entry.message}
                for entry in ctx.audit_log
            ]
            st.table(log_data)
        else:
            st.info("No audit log entries yet.")
