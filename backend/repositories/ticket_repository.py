from supabase import create_client
from core.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# INSERT TICKET (CLEAN ARCHITECTURE)
# ─────────────────────────────────────────────
async def insert_ticket(data):
    try:
        data = dict(data)

        # embedding safety
        if data.get("embedding") is not None:
            data["embedding"] = [float(x) for x in data["embedding"]]

        # ONLY SAFE DEFAULTS (NO BUSINESS LOGIC HERE)
        data.setdefault("priority", "P5")
        data.setdefault("priority_label", "Planning")
        data.setdefault("sla_response_time", None)
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
                "match_count": top_k
            }
        ).execute()

        return res.data or []

    except Exception as e:
        print("❌ vector search error:", str(e))
        return []


# ─────────────────────────────────────────────
# DELETE SINGLE
# ─────────────────────────────────────────────
async def delete_ticket(issue_key):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .eq("issue_key", issue_key) \
            .execute()

        return bool(res.data)

    except Exception as e:
        print("❌ delete_ticket error:", str(e))
        return False


# ─────────────────────────────────────────────
# DELETE CASCADE
# ─────────────────────────────────────────────
async def delete_ticket_cascade(parent_key: str):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}") \
            .execute()

        return bool(res.data)

    except Exception as e:
        print("❌ delete_ticket_cascade error:", str(e))
        return False


# ─────────────────────────────────────────────
# UPDATE STATUS CASCADE
# ─────────────────────────────────────────────
async def update_status_cascade(parent_key: str, status: str):
    try:
        parent_key = parent_key.strip()

        res = supabase.table("tickets") \
            .update({"status": status}) \
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}") \
            .execute()

        return bool(res.data)

    except Exception as e:
        print("❌ update_status_cascade error:", str(e))
        return False


# ─────────────────────────────────────────────
# PRIORITY + SLA UPDATE (FIXED + SAFE)
# ─────────────────────────────────────────────
async def update_ticket_priority(issue_key: str, priority: str, sla: dict, label: str):
    try:
        sla = sla or {}

        payload = {
            "priority": priority,
            "priority_label": label,
            "sla_response_time": sla.get("response_time"),
            "sla_resolution_time": sla.get("resolution_time")
        }

        res = supabase.table("tickets") \
            .update(payload) \
            .eq("issue_key", issue_key) \
            .execute()

        # ✅ correct Supabase error handling
        if hasattr(res, "error") and res.error:
            print("❌ update_ticket_priority failed:", res.error)
            return False

        # optional safety check
        if not res.data:
            print("⚠️ update_ticket_priority: no rows updated")
            return False

        return True

    except Exception as e:
        print("❌ update_ticket_priority error:", str(e))
        return False

