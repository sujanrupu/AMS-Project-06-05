from supabase import create_client
from core.config import Config

# Supabase client initialization
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# Insert new ticket into DB
async def insert_ticket(data):
    try:
        res = supabase.table("tickets").insert(data).execute()

        if res.data:
            return res.data[0]

        print("❌ insert_ticket: No data returned")
        return None

    except Exception as e:
        print("❌ insert_ticket error:", str(e))
        return None


# Fetch all tickets from DB
async def get_all_tickets():
    try:
        res = supabase.table("tickets").select("*").execute()
        return res.data if res.data else []

    except Exception as e:
        print("❌ get_all_tickets error:", str(e))
        return []


# Delete a single ticket by issue_key
async def delete_ticket(issue_key):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .eq("issue_key", issue_key) \
            .execute()

        return True if res.data is not None else False

    except Exception as e:
        print("❌ delete_ticket error:", str(e))
        return False


# Delete parent + child tickets together
async def delete_ticket_cascade(parent_key: str):
    try:
        res = supabase.table("tickets") \
            .delete() \
            .or_(f"issue_key.eq.{parent_key},parent_ticket_key.eq.{parent_key}") \
            .execute()

        return True if res.data is not None else False

    except Exception as e:
        print("❌ delete_ticket_cascade error:", str(e))
        return False


# Update status for parent + children in one query
async def update_status_cascade(parent_key: str, status: str):
    """
    Single-query cascade update for parent + child tickets
    """

    try:
        parent_key = parent_key.strip()

        print("🔍 Updating status for:", parent_key)

        # Update both parent and children in one DB call
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