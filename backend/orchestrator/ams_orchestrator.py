from modules.duplicate_detection.handler import handle_duplicate_flow
from modules.priority_sla.handler        import handle_priority_sla
from modules.runbook_execution.handler   import handle_runbook_flow

from repositories.ticket_repository import update_ticket_priority

from services.slack_service import send_to_slack


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────
async def handle_ticket(data):

    state = {
        "data":    data,
        "summary": getattr(data, "summary", "") if data else "",
        "type":    None,
        "id":      None,
        "message": None,

        # priority/sla defaults
        "priority":             None,
        "priority_label":       None,
        "sla_response_time":    None,
        "sla_resolution_time":  None,
        "is_duplicate":         False,

        # runbook defaults
        "runbook_title":    None,
        "runbook_category": None,
        "runbook_owner": None,
        "runbook_ci_asset": None,
        "match_type":       None,
        "checklist_steps":  [],
        "commands":         [],
    }

    try:

        # ─────────────────────────────
        # STEP 1 — DUPLICATE DETECTION
        # ─────────────────────────────
        state = await safe_run_module(handle_duplicate_flow, state)

        # summary safety fallback
        if not state.get("summary") and state.get("data"):
            data_obj = state["data"]
            state["summary"] = getattr(data_obj, "summary", "") \
                if hasattr(data_obj, "summary") else ""

        # Stop pipeline immediately if duplicate
        if state.get("is_duplicate"):
            return normalize_response(state)

        # ─────────────────────────────
        # STEP 2 — PRIORITY + SLA
        # ─────────────────────────────
        state = await safe_run_module(handle_priority_sla, state)

        # Persist priority + SLA to DB
        issue_key = state.get("id")
        if issue_key:
            await update_ticket_priority(
                issue_key=issue_key,
                priority=state.get("priority"),
                sla={
                    "response_time":    state.get("sla_response_time"),
                    "resolution_time":  state.get("sla_resolution_time")
                },
                label=state.get("priority_label")
            )

        # ─────────────────────────────
        # STEP 3 — RUNBOOK EXECUTION
        # ─────────────────────────────
        state = await safe_run_module(handle_runbook_flow, state)
        return normalize_response(state)

    except Exception as e:
        return {
            "type":    "error",
            "message": f"Orchestrator failed: {str(e)}"
        }


# ─────────────────────────────────────────────
# SAFE RUNNER
# ─────────────────────────────────────────────
async def safe_run_module(module_fn, state: dict):
    """
    Runs a module safely.
    Uses state.update(result) so all keys accumulate
    across the pipeline without losing previous state.
    """
    try:
        result = await module_fn(state)

        if not isinstance(result, dict):
            return {
                **state,
                "type":    "error",
                "message": "Module returned invalid state"
            }

        state.update(result)
        return state

    except Exception as e:
        return {
            **state,
            "type":    "error",
            "message": f"Module failed: {str(e)}"
        }


# ─────────────────────────────────────────────
# RESPONSE NORMALIZER
# ─────────────────────────────────────────────
def normalize_response(state: dict):
    return {
        # core
        "type":    state.get("type", "success"),
        "id":      state.get("id"),
        "message": state.get("message"),

        # priority + SLA
        "priority":            state.get("priority"),
        "priority_label":      state.get("priority_label"),
        "sla_response_time":   state.get("sla_response_time"),
        "sla_resolution_time": state.get("sla_resolution_time"),

        # runbook execution
        "runbook": {
            "title":      state.get("runbook_title"),
            "category":   state.get("runbook_category"),
            "owner":      state.get("runbook_owner"),
            "ci_asset":   state.get("runbook_ci_asset"),
            "match_type": state.get("match_type"),
        } if state.get("match_type") else None,

        "checklist_steps": state.get("checklist_steps", []),
        "commands":        state.get("commands", []),
    }