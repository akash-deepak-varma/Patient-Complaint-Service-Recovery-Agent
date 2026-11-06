# Patient Complaint & Service Recovery Agent — Implementation Plan

## Top-Level Overview

**Goal:** Build a multi-agent system that automatically handles patient complaints received via email. Coordinated agents categorize, extract, route, respond to, and track complaints — reducing resolution time and improving empathetic communication. A Streamlit web UI ties everything together, giving operators a visual dashboard to submit complaints, inspect pipeline results, and monitor resolution status.

**Scope:** Six specialized agents wired together with a shared complaint context object, an orchestrator that drives the pipeline, and a Streamlit front-end for human interaction and visibility.

**Approach:** Each agent is independently implemented with a defined input/output contract. A shared `ComplaintContext` Pydantic model flows between agents. The orchestrator runs the pipeline. The Streamlit app calls the orchestrator and renders results.

## Confirmed Design Decisions

| Decision | Choice |
|----------|--------|
| LLM / API | OpenAI Codex API via the `openai` Python SDK (`gpt-3.5-turbo` model) |
| API Key | Loaded from environment variable `OPENAI_API_KEY` — never hardcoded |
| Resolution status updates | Pipeline-only (no manual UI controls in the Streamlit app) |
| Patient history data | Mock JSON fixtures in `data/mock_patient_history.json` |

---

## Sub-Tasks

---

### Sub-Task 1 — Define the Complaint Context Schema

**Intent:** Establish the shared data structure that all agents read from and write to. Every downstream agent and the UI depend on this schema.

**Expected Outcomes:**
- A Pydantic model `ComplaintContext` in `models/complaint_context.py`
- Fields cover: complaint ID, raw email text, category, extracted entities, case history, assigned department, escalation level, response draft, resolution status, and audit log
- `ResolutionStatus` and `EscalationLevel` enums defined in the same file
- Model is importable by all agents and the orchestrator

**Todo List:**
1. Create `models/complaint_context.py`
2. Define `ResolutionStatus` enum: OPEN, IN_PROGRESS, RESOLVED, ESCALATED
3. Define `EscalationLevel` enum: NONE, LOW, HIGH, CRITICAL
4. Define `ComplaintCategory` enum: BILLING, SCHEDULING, STAFF_BEHAVIOUR, FACILITY, CLINICAL_QUALITY, OTHER
5. Define `ComplaintContext` Pydantic model with all fields, types, defaults, and docstrings
6. Write a unit test confirming the model initialises with correct defaults

**Relevant Context:**
- All agents import `ComplaintContext` from `models/complaint_context.py`
- Streamlit UI (Sub-Task 9) renders fields from this model directly

**Status:** [ ] pending

---

### Sub-Task 2 — Intake Agent (Categorization)

**Intent:** Read the raw complaint email and classify it into a complaint category and produce a one-sentence summary. This determines downstream routing and investigation workflow.

**Expected Outcomes:**
- `agents/intake_agent.py` implemented
- Writes `category` and `summary` onto `ComplaintContext`

**Todo List:**
1. Create `agents/intake_agent.py`
2. Write a prompt template instructing an LLM to classify the complaint and summarise it
3. Parse LLM output and map to `ComplaintCategory` enum
4. Write result onto `ComplaintContext`
5. Add tests with sample emails covering multiple categories

**Relevant Context:**
- Input: `ComplaintContext.raw_email`
- Output: `ComplaintContext.category`, `ComplaintContext.summary`

**Status:** [ ] pending

---

### Sub-Task 3 — Extraction Agent (Entity Extraction)

**Intent:** Extract structured entities from the complaint email: patient name, appointment ID, department, service date, and staff references. Used by History and Routing agents.

**Expected Outcomes:**
- `agents/extraction_agent.py` implemented
- Writes extracted entity fields onto `ComplaintContext`
- Missing fields default to None gracefully

**Todo List:**
1. Create `agents/extraction_agent.py`
2. Write a prompt instructing the LLM to return extracted entities as JSON
3. Parse the JSON and populate the matching `ComplaintContext` fields
4. Handle missing fields by setting them to None
5. Add tests with a fully-populated email and a partial email

**Relevant Context:**
- Input: `ComplaintContext.raw_email`
- Output: `ComplaintContext.patient_name`, `ComplaintContext.appointment_id`, `ComplaintContext.department`, `ComplaintContext.service_date`, `ComplaintContext.staff_references`

**Status:** [ ] pending

---

### Sub-Task 4 — History Agent (Case History Retrieval)

**Intent:** Retrieve prior complaint cases and interaction notes for the patient using extracted identifiers. Enables personalised responses and detection of repeat issues.

**Expected Outcomes:**
- `agents/history_agent.py` implemented
- Looks up mock history by patient name or appointment ID
- Writes results to `ComplaintContext.case_history`

**Todo List:**
1. Create `agents/history_agent.py`
2. Create `data/mock_patient_history.json` with sample patient records and prior cases
3. Implement lookup by `patient_name` and/or `appointment_id`
4. Write results to `ComplaintContext.case_history` as a list of prior case summary strings
5. Add tests for a known patient and an unknown patient

**Relevant Context:**
- Input: `ComplaintContext.patient_name`, `ComplaintContext.appointment_id`
- Output: `ComplaintContext.case_history`

**Status:** [ ] pending

---

### Sub-Task 5 — Routing Agent (Department Routing and Escalation)

**Intent:** Assign the complaint to the correct department and determine the escalation level based on category, sensitive keywords, and repeat history.

**Expected Outcomes:**
- `agents/routing_agent.py` implemented
- Sets `ComplaintContext.assigned_department` and `ComplaintContext.escalation_level`

**Todo List:**
1. Create `agents/routing_agent.py`
2. Implement a routing table mapping `ComplaintCategory` to a responsible department string
3. Implement escalation logic: keyword scan (legal, unsafe, injury, death) and repeat-complaint check from `case_history`
4. Set `assigned_department` and `escalation_level` on the context
5. Add tests for standard routing, keyword escalation, and repeat-complaint escalation

**Relevant Context:**
- Input: `ComplaintContext.category`, `ComplaintContext.raw_email`, `ComplaintContext.case_history`
- Output: `ComplaintContext.assigned_department`, `ComplaintContext.escalation_level`

**Status:** [ ] pending

---

### Sub-Task 6 — Response Agent (Empathetic Draft Generation)

**Intent:** Draft a professional, empathetic reply email to the patient. For escalated complaints, the draft includes heightened urgency and apology language.

**Expected Outcomes:**
- `agents/response_agent.py` implemented
- Writes full draft email to `ComplaintContext.response_draft`

**Todo List:**
1. Create `agents/response_agent.py`
2. Write a prompt template using patient name, summary, assigned department, and escalation level
3. Draft must acknowledge the complaint, thank the patient, name the follow-up contact, and state a timeframe
4. Add escalation-specific language when `escalation_level` is HIGH or CRITICAL
5. Write result to `ComplaintContext.response_draft`
6. Add tests comparing tone between standard and escalated complaints

**Relevant Context:**
- Input: `ComplaintContext.patient_name`, `ComplaintContext.summary`, `ComplaintContext.assigned_department`, `ComplaintContext.escalation_level`
- Output: `ComplaintContext.response_draft`

**Status:** [ ] pending

---

### Sub-Task 7 — Tracker Agent (Resolution Lifecycle Tracking)

**Intent:** Manage the complaint lifecycle by updating resolution status and maintaining a timestamped audit log of every state transition.

**Expected Outcomes:**
- `agents/tracker_agent.py` implemented
- Valid status transitions applied to `ComplaintContext.resolution_status`
- Audit log entries appended with timestamps

**Todo List:**
1. Create `agents/tracker_agent.py`
2. Implement `update_status(context, new_status)` with transition validation
3. Append a timestamped log entry to `ComplaintContext.audit_log` on every change
4. Raise a descriptive error for invalid transitions such as RESOLVED to OPEN
5. Add tests for valid and invalid transitions

**Relevant Context:**
- Input/Output: `ComplaintContext.resolution_status`, `ComplaintContext.audit_log`
- `ResolutionStatus` enum from `models/complaint_context.py`

**Status:** [ ] pending

---

### Sub-Task 8 — Orchestrator (Pipeline Wiring)

**Intent:** Wire all six agents into a single sequential pipeline. Accepts a raw email string and returns a fully populated `ComplaintContext`.

**Expected Outcomes:**
- `orchestrator.py` with `run_pipeline(raw_email: str) -> ComplaintContext`
- Agents called in order: Intake, Extraction, History, Routing, Response, Tracker
- CLI entry point for local testing

**Todo List:**
1. Create `orchestrator.py`
2. Instantiate and call each agent in sequence, passing the same `ComplaintContext` through
3. Set initial resolution status to IN_PROGRESS via the Tracker Agent
4. Log each agent's key outputs after it runs
5. Expose `run_pipeline(raw_email: str) -> ComplaintContext`
6. Add `__main__` block with a sample complaint for `python orchestrator.py`
7. Add an end-to-end integration test with a realistic complaint email

**Relevant Context:**
- Imports all agents from `agents/`
- Imports `ComplaintContext` from `models/complaint_context.py`
- Called directly by the Streamlit app (Sub-Task 9)
- All prior sub-tasks must be complete before this one

**Status:** [ ] pending

---

### Sub-Task 9 — Streamlit UI (Operator Dashboard)

**Intent:** Build a Streamlit web application that lets operators submit complaint emails, watch the pipeline run, and inspect all outputs — categorization, extracted entities, routing decision, draft response, escalation status, and audit log — in a clean, readable interface.

**Expected Outcomes:**
- `app.py` Streamlit application implemented
- Operator can paste or type a complaint email and click Run
- Results are displayed in clearly labeled sections with colour-coded escalation indicators
- Draft response is shown in an editable text area so operators can adjust before sending
- Audit log is shown as a timeline at the bottom of the page

**Todo List:**
1. Create `app.py` with `streamlit` as the sole new dependency
2. Add a wide-layout page config with a title: Patient Complaint & Service Recovery Agent
3. Add a `st.text_area` for complaint email input and a Run Pipeline button
4. On button click, call `run_pipeline(raw_email)` from `orchestrator.py` and store the returned `ComplaintContext` in `st.session_state`
5. Display results in the following sections using `st.expander` or `st.columns`:
   - **Complaint Summary** — category badge and one-line summary
   - **Extracted Details** — patient name, appointment ID, department, service date, staff references
   - **Case History** — prior cases as a bullet list, or "No prior history found" if empty
   - **Routing Decision** — assigned department and escalation level (colour-coded: green for NONE, orange for LOW/HIGH, red for CRITICAL)
   - **Draft Response** — editable `st.text_area` pre-filled with `ComplaintContext.response_draft`
   - **Audit Log** — timestamped entries displayed as a table
6. Add a sidebar with a brief description of the system and how to use it
7. Add `requirements.txt` listing all dependencies including `streamlit`
8. Test the UI manually with at least two sample complaints: one standard and one escalated

**Relevant Context:**
- Calls `run_pipeline` from `orchestrator.py`
- All `ComplaintContext` fields rendered here; any schema change in Sub-Task 1 may need a UI update
- Run locally with `streamlit run app.py`

**Status:** [ ] pending

---

## Implementation Order

Sub-Task 1 (Schema) must be done first — all agents and the UI depend on it.
Sub-Tasks 2 through 7 (Agents) can be done in any order after Sub-Task 1.
Sub-Task 8 (Orchestrator) requires Sub-Tasks 1 through 7 to be complete.
Sub-Task 9 (Streamlit UI) requires Sub-Task 8 to be complete.

---

## Project Structure (Target)

```
/
├── models/
│   └── complaint_context.py        # Shared schema, enums
├── agents/
│   ├── intake_agent.py             # Categorization
│   ├── extraction_agent.py         # Entity extraction
│   ├── history_agent.py            # Case history retrieval
│   ├── routing_agent.py            # Department routing and escalation
│   ├── response_agent.py           # Empathetic response drafting
│   └── tracker_agent.py            # Resolution lifecycle tracking
├── data/
│   └── mock_patient_history.json   # Mock patient and case history data
├── tests/
│   └── ...                         # Unit and integration tests
├── orchestrator.py                 # End-to-end pipeline
├── app.py                          # Streamlit operator dashboard
├── requirements.txt                # Python dependencies
└── complaint-agent-plan.md         # This plan file
```
