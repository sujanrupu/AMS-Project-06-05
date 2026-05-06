from .agent import pick_best_match, generate_fresh_rca
from .service import get_confidence_label, get_rca_summary


async def handle_rca_flow(state: dict) -> dict:
    try:
        summary      = state.get("summary", "")
        similar_past = state.get("similar_past", [])
        description  = ""

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

        current = {"summary": summary, "description": description}

        # ── PATH A: similar tickets found — LLM picks best, return its RCA ──
        if similar_past:
            matched = pick_best_match(current, similar_past)

            if matched:
                confidence = matched.get("rca_confidence", "LOW")
                affected   = matched.get("rca_affected", "Unknown")
                print(f"[RCAHandler] Best match: '{matched.get('issue_key')}' — using its RCA")

                return {
                    **state,
                    "type":                 "rca_complete",
                    "message":              matched.get("rca_root_cause", ""),
                    "rca_root_cause":       matched.get("rca_root_cause", ""),
                    "rca_affected":         affected,
                    "rca_steps":            matched.get("rca_steps", []),
                    "rca_confidence":       confidence,
                    "rca_confidence_label": get_confidence_label(confidence),
                    "rca_summary":          get_rca_summary(confidence, affected),
                }

            # LLM said no meaningful match — fall through to generate
            print("[RCAHandler] LLM found no meaningful match — generating fresh RCA")

        # ── PATH B: no similar tickets or no match — generate fresh RCA ──
        result = generate_fresh_rca(current)

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