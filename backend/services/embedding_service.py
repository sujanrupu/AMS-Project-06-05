from sentence_transformers import SentenceTransformer

# load once
model = SentenceTransformer("all-MiniLM-L6-v2")

async def get_embedding(text: str):
    try:
        embedding = model.encode(text).tolist()
        return embedding
    except Exception as e:
        print("❌ embedding error:", str(e))
        return None