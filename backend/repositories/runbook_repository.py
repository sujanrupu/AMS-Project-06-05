from supabase import create_client
from core.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ─────────────────────────────────────────────
# VECTOR SEARCH
# ─────────────────────────────────────────────
async def search_runbooks_by_vector(embedding: list[float], top_k: int = 1) -> list[dict]:
    try:
        if not embedding:
            return []

        embedding = [float(x) for x in embedding]

        res = supabase.rpc(
            "match_runbooks",
            {
                "query_embedding": embedding,
                "match_count":     top_k,
            }
        ).execute()

        if res.data:
            return res.data

        print("⚠️ No matches found from vector search")
        return []

    except Exception as e:
        print(f"❌ search_runbooks_by_vector error: {e}")
        return []


# ─────────────────────────────────────────────
# INSERT RUNBOOK
# ─────────────────────────────────────────────
async def insert_runbook(data: dict) -> dict | None:
    try:
        res = supabase.table("runbooks").insert(data).execute()

        if res.data:
            return res.data[0]

        print("❌ insert_runbook: No data returned")
        return None

    except Exception as e:
        print(f"❌ insert_runbook error: {e}")
        return None