from supabase import create_client
from core.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ───────────── INSERT ─────────────
async def insert_ticket(data):
    try:
        res = supabase.table("tickets").insert(data).execute()

        if hasattr(res, "data") and res.data:
            return res.data[0]   # ✅ return clean row

        return None

    except Exception as e:
        print("❌ insert_ticket error:", str(e))
        return None


# ───────────── GET ALL ─────────────
async def get_all_tickets():
    try:
        res = supabase.table("tickets").select("*").execute()

        if hasattr(res, "data") and res.data:
            return res.data

        return []

    except Exception as e:
        print("❌ get_all_tickets error:", str(e))
        return []


# ───────────── DELETE ─────────────
async def delete_ticket(issue_key):
    try:
        res = supabase.table("tickets").delete().eq("issue_key", issue_key).execute()
        return res

    except Exception as e:
        print("❌ delete_ticket error:", str(e))
        return None