from .agent import analyze_async
from .service import map_priority, get_label, get_sla


def clean(value):
    """Robust normalization to prevent mapping bugs"""
    value = str(value or "").strip().lower()

    if "high" in value:
        return "High"
    if "medium" in value:
        return "Medium"
    if "low" in value:
        return "Low"

    return "Medium"


def safe_dict(obj):
    """Convert Pydantic / object → dict safely"""
    if obj is None:
        return {}

    if hasattr(obj, "model_dump"):   # Pydantic v2
        return obj.model_dump()

    if hasattr(obj, "dict"):         # Pydantic v1
        return obj.dict()

    if hasattr(obj, "__dict__"):
        return vars(obj)

    return obj if isinstance(obj, dict) else {}


async def handle_priority_sla(state: dict):
    try:
        # ─────────────────────────────────────────────
        # FIX: SAFE DATA EXTRACTION (CRITICAL)
        # ─────────────────────────────────────────────
        data = safe_dict(state.get("data"))

        description = data.get("description", "")

        urgency = "Medium"
        impact = "Medium"
        rationale = "No rationale provided"

        print("INPUT DESCRIPTION:", description)

        # ─────────────────────────────────────────────
        # LLM CLASSIFICATION
        # ─────────────────────────────────────────────
        if isinstance(description, str) and len(description.strip()) >= 5:
            llm_result = await analyze_async(description)

            print("LLM RAW OUTPUT:", llm_result)

            if isinstance(llm_result, dict):
                urgency = clean(llm_result.get("urgency"))
                impact = clean(llm_result.get("impact"))
                rationale = llm_result.get("rationale", rationale)

        print("NORMALIZED URGENCY:", urgency)
        print("NORMALIZED IMPACT:", impact)

        # ─────────────────────────────────────────────
        # PRIORITY CALCULATION
        # ─────────────────────────────────────────────
        priority = map_priority(urgency, impact)
        label = get_label(priority)
        sla = get_sla(priority)

        print("FINAL PRIORITY:", priority)

        # ─────────────────────────────────────────────
        # RESPONSE
        # ─────────────────────────────────────────────
        return {
            **state,

            "priority": priority,
            "priority_label": label,

            "sla_response_time": sla["response_time"],
            "sla_resolution_time": sla["resolution_time"],

            "rationale": rationale
        }

    except Exception as e:
        print("❌ PRIORITY ERROR:", str(e))

        return {
            **state,

            "priority": "P5",
            "priority_label": "Planning",
            "sla_response_time": "16 hours",
            "sla_resolution_time": "48 hours",

            "rationale": f"System fallback: {str(e)}"
        }