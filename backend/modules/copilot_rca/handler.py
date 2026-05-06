from .agent import is_same_issue, generate_fresh_rca
from .service import get_confidence_label, get_rca_summary


async def handle_rca_flow(state: dict) -> dict:
    try:
        summary     = state.get("summary", "")
        description = ""

        raw_data = state.get("data")
        if raw_data:
            if hasattr(raw_data, "description"):
                description = raw_data.description or ""
            elif isinstance(raw_data, dict):
                description = raw_data.get("description", "")

        if not summary:
            return {
                **state,
                "type":    "error",
                "message": "RCA module: ticket summary is empty",
            }

        if not description:
            return {
                **state,
                "type":    "error",
                "message": "RCA module: ticket description is empty",
            }

        result = generate_fresh_rca({"summary": summary, "description": description})

        if result.get("status") == "error":
            return {
                **state,
                "type":    "error",
                "message": result.get("root_cause", "RCA generation failed"),
            }

        confidence = result.get("confidence", "LOW")
        affected   = result.get("affected_component", "Unknown")

        return {
            **state,
            "type":                 "rca_complete",
            "message":              result.get("root_cause", ""),
            "rca_root_cause":       result.get("root_cause", ""),
            "rca_affected":         affected,
            "rca_steps":            result.get("resolution_steps", []),
            "rca_confidence":       confidence,
            "rca_confidence_label": get_confidence_label(confidence),
            "rca_summary":          get_rca_summary(confidence, affected),
        }

    except Exception as e:
        print(f"❌ handle_rca_flow error: {e}")
        return {
            **state,
            "type":    "error",
            "message": f"RCA module failed: {str(e)}",
        }