"""
Simple + scalable orchestrator (NO LangGraph)

Design:
- Each module modifies state safely
- Orchestrator ensures state integrity
- Frontend receives only clean output
"""

from modules.duplicate_detection.handler import handle_duplicate_flow


# ───────────── MAIN ORCHESTRATOR ─────────────
async def handle_ticket(data):
    """
    Entry point for ticket processing pipeline
    """

    # ───────────── INITIAL STATE ─────────────
    state = {
        "data": data,
        "summary": getattr(data, "summary", "") if data else "",
        "type": None,
        "id": None,
        "message": None
    }

    try:
        # ───────────── STEP 1: DUPLICATE CHECK ─────────────
        state = await safe_run_module(handle_duplicate_flow, state)

        # ───────────── FUTURE MODULES ─────────────
        # state = await safe_run_module(handle_priority_flow, state)
        # state = await safe_run_module(handle_rca_flow, state)

        return normalize_response(state)

    except Exception as e:
        return {
            "type": "error",
            "message": f"Orchestrator failed: {str(e)}"
        }


# ───────────── SAFE MODULE WRAPPER ─────────────
async def safe_run_module(module_fn, state: dict):
    """
    Prevents one module from breaking entire pipeline
    """

    try:
        result = await module_fn(state)

        if not isinstance(result, dict):
            return {
                **state,
                "type": "error",
                "message": "Module returned invalid state"
            }

        return result

    except Exception as e:
        return {
            **state,
            "type": "error",
            "message": f"Module failed: {str(e)}"
        }


# ───────────── RESPONSE NORMALIZER ─────────────
def normalize_response(state: dict):
    """
    Ensures frontend always gets safe output
    """

    return {
        "type": state.get("type", "error"),
        "id": state.get("id"),
        "message": state.get("message")
    }