# modules/runbook_execution/handler.py

from modules.runbook_execution.agent import RunbookAgent


async def handle_runbook_flow(state: dict) -> dict:
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
                "message": "Runbook module: ticket summary is empty",
            }

        if not description:
            return {
                **state,
                "type":    "error",
                "message": "Runbook module: ticket description is empty",
            }

        agent  = RunbookAgent()
        result = await agent.run(
            summary=summary,
            description=description,
            state=state,
        )

        return {
            **state,
            "runbook_title":           result.get("runbook_title"),
            "runbook_category":        result.get("runbook_category"),
            "runbook_escalation_team": result.get("runbook_escalation_team"),
            "checklist_steps":         result.get("checklist_steps", []),
            "commands":                result.get("commands", []),
            "match_type":              result.get("match_type", "ai_fallback"),
            "type":                    state.get("type") or "runbook_executed",
            "message":                 result.get("message", "Runbook execution complete"),
        }

    except Exception as e:
        print(f"❌ handle_runbook_flow error: {e}")
        return {
            **state,
            "type":    "error",
            "message": f"Runbook module failed: {str(e)}",
        }