import os
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

# ── Load env ──
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ── Init clients ──
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")

# ── Build embedding text ──
def build_text(r):
    return f"""
    Title: {r['title']}
    Category: {r['category']}
    Symptoms: {r['symptoms']}
    Keywords: {r['keywords']}
    Resolution: {r['resolution_steps']}
    """

# ── Fetch runbooks ──
res = supabase.table("runbooks").select("*").execute()

if not res.data:
    print("❌ No runbooks found")
    exit()

print(f"🔍 Found {len(res.data)} runbooks")

# ── Generate + store embeddings ──
for r in res.data:
    try:
        text = build_text(r)

        embedding = model.encode(text).tolist()

        supabase.table("runbooks").update({
            "embedding": embedding
        }).eq("id", r["id"]).execute()

        print(f"✅ Embedded: {r['title']}")

    except Exception as e:
        print(f"❌ Failed for {r['title']}: {e}")

print("🎉 All embeddings stored successfully!")