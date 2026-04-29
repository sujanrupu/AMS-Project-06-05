from modules.duplicate_detection.handler import handle_duplicate_flow


# Main orchestrator entry point for ticket processing
async def handle_ticket(data):
    """
    Executes full ticket pipeline step-by-step
    """

    # Initial pipeline state
    state = {
        "data": data,
        "summary": getattr(data, "summary", "") if data else "",
        "type": None,
        "id": None,
        "message": None
    }

    try:
        # Step 1: Duplicate detection module
        state = await safe_run_module(handle_duplicate_flow, state)

        # Future enhancements (priority, RCA, etc.)
        # state = await safe_run_module(handle_priority_flow, state)
        # state = await safe_run_module(handle_rca_flow, state)

        return normalize_response(state)

    except Exception as e:
        return {
            "type": "error",
            "message": f"Orchestrator failed: {str(e)}"
        }


# Safe wrapper to isolate module failures
async def safe_run_module(module_fn, state: dict):
    """
    Runs a module safely without breaking pipeline
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


# Normalize response for frontend consistency
def normalize_response(state: dict):
    """
    Ensures API response is always clean and predictable
    """

    return {
        "type": state.get("type", "error"),
        "id": state.get("id"),
        "message": state.get("message")
    }