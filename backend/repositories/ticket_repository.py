# repositories/ticket_repository.py

from supabase import create_client
from core.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# INSERT TICKET
# ─────────────────────────────────────────────
async def insert_ticket(data):
    try:
        data = dict(data)

        # embedding safety
        if data.get("embedding") is not None:
            data["embedding"] = [float(x) for x in data["embedding"]]

        # safe defaults — no business logic
        data.setdefault("priority",            "P5")
        data.setdefault("priority_label",      "Planning")
        data.setdefault("sla_response_time",   None)
        data.setdefault("sla_resolution_time", None)

        res = supabase.table("tickets").insert(data).execute()
        return res.data[0] if res.data else None

    except Exception as e:
        print("❌ insert_ticket error:", str(e))
        return None


# ─────────────────────────────────────────────
# GET ALL TICKETS
# ─────────────────────────────────────────────
async def get_all_tickets():
    try:
        res = supabase.table("tickets").select("*").execute()
        return res.data or []

    except Exception as e:
        print("❌ get_all_tickets error:", str(e))
        return []


# ─────────────────────────────────────────────
# VECTOR SEARCH
# ─────────────────────────────────────────────
async def search_similar_tickets(query_embedding, top_k=5):
    try:
        if not query_embedding:
            return []

        query_embedding = [float(x) for x in query_embedding]

        res = supabase.rpc(
            "match_tickets",
            {
                "query_embedding": query_embedding,
                "match_count":     top_k,
            }
        ).execute()

        return res.data or []

    except Exception as e:
        print("❌ vector search error:", str(e))
        return []


# ─────────────────────────────────────────────
# DELETE SINGLE TICKET
# ─────────────────────────────────────────────
async def delete_ticket(issue_key: str):
    try:
        res = (
            supabase.table("tickets")
            .delete()
            .eq("issue_key", issue_key)
            .execute()
        )
        return bool(res.data)

    except Exception as e:
        print("❌ delete_ticket error:", str(e))
        return False


# ─────────────────────────────────────────────
# DELETE CASCADE (PARENT + CHILDREN)
# ─────────────────────────────────────────────
async def delete_ticket_cascade(parent_key: str):
    try:
        res = (
            supabase.table("tickets")
            .delete()
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}")
            .execute()
        )
        return bool(res.data)

    except Exception as e:
        print("❌ delete_ticket_cascade error:", str(e))
        return False


# ─────────────────────────────────────────────
# UPDATE STATUS CASCADE
# ─────────────────────────────────────────────
async def update_status_cascade(parent_key: str, status: str):
    try:
        res = (
            supabase.table("tickets")
            .update({"status": status})
            .or_(f"issue_key.eq.{parent_key.strip()},parent_ticket_key.eq.{parent_key.strip()}")
            .execute()
        )
        return bool(res.data)

    except Exception as e:
        print("❌ update_status_cascade error:", str(e))
        return False


# ─────────────────────────────────────────────
# UPDATE PRIORITY + SLA
# ─────────────────────────────────────────────
async def update_ticket_priority(issue_key: str, priority: str, sla: dict, label: str):
    try:
        sla = sla or {}

        payload = {
            "priority":            priority,
            "priority_label":      label,
            "sla_response_time":   sla.get("response_time"),
            "sla_resolution_time": sla.get("resolution_time"),
        }

        res = (
            supabase.table("tickets")
            .update(payload)
            .eq("issue_key", issue_key)
            .execute()
        )

        if hasattr(res, "error") and res.error:
            print("❌ update_ticket_priority failed:", res.error)
            return False

        if not res.data:
            print("⚠️  update_ticket_priority: no rows updated")
            return False

        return True

    except Exception as e:
        print("❌ update_ticket_priority error:", str(e))
        return False


# ─────────────────────────────────────────────
# UPDATE TICKET RUNBOOK
# Only persists: checklist_steps, commands,
#                runbook_title, runbook_category, match_type
# ─────────────────────────────────────────────
async def update_ticket_runbook(
    issue_key:               str,
    checklist_steps:         list,
    commands:                list,
    runbook_title:           str = None,
    runbook_category:        str = None,
    runbook_escalation_team: str = None,
    match_type:              str = None,
) -> bool:
    try:
        res = (
            supabase.table("tickets")
            .update({
                "checklist_steps":         checklist_steps,
                "commands":                commands,
                "runbook_title":           runbook_title,
                "runbook_category":        runbook_category,
                "runbook_escalation_team": runbook_escalation_team,
                "match_type":              match_type,
            })
            .eq("issue_key", issue_key)
            .execute()
        )
        return bool(res.data)

    except Exception as e:
        print(f"❌ update_ticket_runbook error: {e}")
        return False