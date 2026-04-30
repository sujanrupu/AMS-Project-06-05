from supabase import create_client
from core.config import Config

# Supabase client initialization
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# INSERT TICKET
# ─────────────────────────────────────────────
async def insert_ticket(data):
    try:
        # 🔥 ensure embedding is proper list of float
        if "embedding" in data and data["embedding"] is not None:
            data["embedding"] = [float(x) for x in data["embedding"]]

        res = supabase.table("tickets").insert(data).execute()

        if res.data:
            return res.data[0]

        print("❌ insert_ticket: No data returned")
        return None

    except Exception as e:
        print("❌ insert_ticket error:", str(e))
        return None


# ─────────────────────────────────────────────
# GET ALL TICKETS
# ─────────────────────────────────────────────
async def get_all_tickets():
    try:
        res = supabase.table("tickets").select("*").execute()
        return res.data if res.data else []

    except Exception as e:
        print("❌ get_all_tickets error:", str(e))
        return []


# ─────────────────────────────────────────────
# 🔥 VECTOR SEARCH
# ─────────────────────────────────────────────
async def search_similar_tickets(query_embedding, top_k=5):
    """
    Calls Supabase RPC function: match_tickets
    Returns top similar parent tickets
    """

    try:
        if not query_embedding:
            return []

        # 🔥 ensure proper format
        query_embedding = [float(x) for x in query_embedding]

        res = supabase.rpc(
            "match_tickets",
            {
                "query_embedding": query_embedding,
                "match_count": top_k
            }
        ).execute()

        if res.data:
            return res.data

        print("⚠️ No vector matches found")
        return []

    except Exception as e:
        print("❌ vector search error:", str(e))
        return []


# ─────────────────────────────────────────────
# DELETE SINGLE TICKET
# ─────────────────────────────────────────────
async def delete_ticket(issue_key):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .eq("issue_key", issue_key) \
            .execute()

        return bool(res.data is not None)

    except Exception as e:
        print("❌ delete_ticket error:", str(e))
        return False


# ─────────────────────────────────────────────
# DELETE CASCADE (PARENT + CHILD)
# ─────────────────────────────────────────────
async def delete_ticket_cascade(parent_key: str):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}") \
            .execute()

        return bool(res.data is not None)

    except Exception as e:
        print("❌ delete_ticket_cascade error:", str(e))
        return False


# ─────────────────────────────────────────────
# UPDATE STATUS CASCADE
# ─────────────────────────────────────────────
async def update_status_cascade(parent_key: str, status: str):
    """
    Single-query cascade update for parent + child tickets
    """

    try:
        parent_key = parent_key.strip()

        print("🔍 Updating status for:", parent_key)

        res = supabase.table("tickets") \
            .update({"status": status}) \
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}") \
            .execute()

        print("✅ Updated rows:", res.data)

        if not res.data:
            print("❌ No rows updated → check parent_key mismatch")
            return False

        print(f"✅ Status updated successfully for {parent_key}")

        return True

    except Exception as e:
        print("❌ update_status_cascade error:", str(e))
        return False