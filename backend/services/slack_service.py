import httpx
from core.config import Config
from services.llm_service import call_llm


# ─────────────────────────────────────────────
# VALID SLACK CHANNELS (SOURCE OF TRUTH)
# ─────────────────────────────────────────────
VALID_CHANNELS = {
    "hardware": "#hardware",
    "network": "#network",
    "deployment": "#deployment",
    "application": "#application",
    "database": "#database",
    "performance": "#performance",
    "storage": "#storage",
}

FALLBACK_CHANNEL = "#incident-triage"


# ─────────────────────────────────────────────
# NORMALIZE INPUT (VERY IMPORTANT)
# ─────────────────────────────────────────────
def normalize(value: str) -> str:
    if not value:
        return ""
    return value.strip().lower()


# ─────────────────────────────────────────────
# STRICT CHANNEL RESOLVER
# ─────────────────────────────────────────────
def resolve_channel(value: str) -> str:
    value = normalize(value)

    if not value:
        return FALLBACK_CHANNEL

    # ───────── CATEGORY MATCH (PRIMARY) ─────────
    if "database" in value:
        return VALID_CHANNELS["database"]
    if "network" in value:
        return VALID_CHANNELS["network"]
    if "deployment" in value:
        return VALID_CHANNELS["deployment"]
    if "application" in value:
        return VALID_CHANNELS["application"]
    if "performance" in value or "perf" in value:
        return VALID_CHANNELS["performance"]
    if "storage" in value:
        return VALID_CHANNELS["storage"]
    if "hardware" in value:
        return VALID_CHANNELS["hardware"]

    # ───────── TEAM FALLBACK MATCH ─────────
    if "dba" in value:
        return VALID_CHANNELS["database"]
    if "sre" in value:
        return VALID_CHANNELS["performance"]
    if "infra" in value:
        return VALID_CHANNELS["storage"]
    if "devops" in value:
        return VALID_CHANNELS["deployment"]

    return FALLBACK_CHANNEL


# ─────────────────────────────────────────────
# AI CATEGORY INFERENCE (FALLBACK ONLY)
# ─────────────────────────────────────────────
async def infer_team_from_ai(summary: str) -> str | None:
    prompt = f"""
You are an incident routing system.

Available categories (STRICT):
database, network, deployment, application, performance, storage, hardware

Return ONLY one word from the list above.
No explanation. No punctuation.

Incident:
{summary}

Answer:
"""

    try:
        response = await call_llm(prompt)
        team = normalize(response)

        if team not in VALID_CHANNELS:
            return None

        return team

    except Exception as e:
        print("❌ AI routing failed:", str(e))
        return None


# ─────────────────────────────────────────────
# SEND TO SLACK (FINAL ROUTING ENGINE)
# ─────────────────────────────────────────────
async def send_to_slack(state: dict):
    try:
        match_type = state.get("match_type")
        category   = state.get("runbook_category")
        summary    = state.get("summary", "")
        incident_id = state.get("id")

        team_used = category  # default to category if present

        # ─────────────────────────────
        # CASE 1: RUNBOOK MATCHED
        # ─────────────────────────────
        if match_type == "runbook_match" and category:
            team_used = category
            channel   = resolve_channel(category)

        # ─────────────────────────────
        # CASE 2: AI FALLBACK ROUTING
        # ─────────────────────────────
        else:
            # if AI decides category
            if not category:
                team_used = await infer_team_from_ai(summary)
            if not team_used:
                team_used = "incident-triage"  # fallback

            category = team_used  # ensure runbook_category is set for frontend
            channel = resolve_channel(team_used)

        # ─────────────────────────────
        # SLACK PAYLOAD
        # ─────────────────────────────
        payload = {
            "channel": channel,
            "text": f"🚨 Incident {incident_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*🚨 Incident:* {incident_id}\n"
                            f"*Summary:* {summary}\n"
                            f"*Priority:* {state.get('priority')}\n"
                        )
                    }
                }
            ]
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {Config.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

        data = res.json()

        return {
            "success": data.get("ok", False),
            "channel": channel,
            "team": team_used,
            "match_type": match_type,
            "category": category,  # <-- add this
        }

    except Exception as e:
        print("❌ Slack exception:", str(e))
        return {
            "success": False,
            "error": str(e),
            "channel": None,
            "team": None,
            "category": None
        }
