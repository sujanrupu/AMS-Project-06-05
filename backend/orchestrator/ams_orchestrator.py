from modules.duplicate_detection.handler import handle_duplicate_flow
from modules.priority_sla.handler import handle_priority_sla

from repositories.ticket_repository import update_ticket_priority


# ─────────────────────────────────────────────
# MAIN ORCHESTRATOR (PRODUCTION FIXED VERSION)
# ─────────────────────────────────────────────
async def handle_ticket(data):

    state = {
        "data": data,
        "summary": getattr(data, "summary", "") if data else "",
        "type": None,
        "id": None,
        "message": None,

        # default empty state
        "priority": None,
        "priority_label": None,
        "sla_response_time": None,
        "sla_resolution_time": None,
        "is_duplicate": False
    }

    try:

        # ─────────────────────────────
        # STEP 1: DUPLICATE DETECTION
        # ─────────────────────────────
        state = await safe_run_module(handle_duplicate_flow, state)

        # ensure summary safety
        if not state.get("summary") and state.get("data"):
            data_obj = state["data"]
            state["summary"] = getattr(data_obj, "summary", "") if hasattr(data_obj) else ""

        # ─────────────────────────────
        # STOP IMMEDIATELY IF DUPLICATE
        # ─────────────────────────────
        if state.get("is_duplicate"):
            return normalize_response(state)

        # ─────────────────────────────
        # STEP 2: PRIORITY + SLA (ONLY FOR NEW TICKETS)
        # ─────────────────────────────
        state = await safe_run_module(handle_priority_sla, state)

        # ─────────────────────────────
        # DATABASE UPDATE (ONLY FOR NEW TICKETS)
        # ─────────────────────────────
        issue_key = state.get("id")

        if issue_key:
            await update_ticket_priority(
                issue_key=issue_key,
                priority=state.get("priority"),
                sla={
                    "response_time": state.get("sla_response_time"),
                    "resolution_time": state.get("sla_resolution_time")
                },
                label=state.get("priority_label")
            )

        return normalize_response(state)

    except Exception as e:
        return {
            "type": "error",
            "message": f"Orchestrator failed: {str(e)}"
        }


# ─────────────────────────────────────────────
# SAFE RUNNER
# ─────────────────────────────────────────────
async def safe_run_module(module_fn, state: dict):
    try:
        result = await module_fn(state)

        if not isinstance(result, dict):
            return {
                **state,
                "type": "error",
                "message": "Module returned invalid state"
            }

        state.update(result)
        return state

    except Exception as e:
        return {
            **state,
            "type": "error",
            "message": f"Module failed: {str(e)}"
        }


# ─────────────────────────────────────────────
# RESPONSE NORMALIZER
# ─────────────────────────────────────────────
def normalize_response(state: dict):
    return {
        "type": state.get("type", "success"),
        "id": state.get("id"),
        "message": state.get("message"),

        "priority": state.get("priority"),
        "priority_label": state.get("priority_label"),
        "sla_response_time": state.get("sla_response_time"),
        "sla_resolution_time": state.get("sla_resolution_time"),
    }