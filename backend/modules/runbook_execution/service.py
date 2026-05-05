# modules/runbook/service.py

from services.embedding_service import get_embedding
from repositories.runbook_repository import search_runbooks_by_vector
from core.constants import RUNBOOK_SIMILARITY_THRESHOLD

# Minimum similarity score to consider a runbook a valid match.
# Below this → AI fallback. Tune if needed.


# ─────────────────────────────────────────────────────────────
# RUNBOOK SEARCH (VECTOR)
# ─────────────────────────────────────────────────────────────
async def fetch_best_runbook(summary: str, description: str) -> dict | None:
    """
    Embeds summary + description, hits Supabase vector search,
    returns top-1 runbook only if similarity >= threshold.
    Returns None → triggers AI fallback in agent.py
    """
    try:
        query = f"{summary} {description}".strip()
        if not query:
            return None

        query_embedding = await get_embedding(query)

        if not query_embedding:
            return None

        query_embedding = [float(x) for x in query_embedding]

        results = await search_runbooks_by_vector(query_embedding, top_k=1)

        if not results:
            return None

        best = results[0]

        # ── CRITICAL FIX ──────────────────────────────────────
        # Without this: zscaler → CPU Usage (wrong, similarity 0.22)
        # With this:    zscaler → None → AI fallback (correct)
        similarity = best.get("similarity", 0)

        if similarity < RUNBOOK_SIMILARITY_THRESHOLD:
            print(
                f"⚠️  Runbook '{best.get('title')}' rejected — "
                f"similarity {similarity:.2f} below threshold {RUNBOOK_SIMILARITY_THRESHOLD}"
            )
            return None

        print(f"✅ Runbook matched: '{best.get('title')}' (similarity: {similarity:.2f})")
        return best

    except Exception as e:
        print(f"❌ fetch_best_runbook error: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# OUTPUT PARSER
# ─────────────────────────────────────────────────────────────
def parse_llm_output(raw: str) -> tuple[list[str], list[str]]:
    steps    = []
    commands = []

    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("STEP:"):
            text = line[5:].strip()
            if text:
                steps.append(text)
        elif line.upper().startswith("CMD:"):
            text = line[4:].strip()
            if text and text.upper() != "N/A":
                commands.append(text)

    # Fallback — if LLM returned plain text with no STEP: prefix
    if not steps and raw.strip():
        steps = [raw.strip()]

    return steps, commands


# ─────────────────────────────────────────────────────────────
# SAFETY FILTER
# ─────────────────────────────────────────────────────────────
_DANGEROUS_PATTERNS = [
    "rm -rf", "drop table", "drop database", "delete from",
    "kill -9", "truncate", "chmod 777", ":(){:|:&};:", "mkfs", "dd if=",
]

def filter_safe_commands(commands: list[str]) -> list[str]:
    safe = []
    for cmd in commands:
        lower = cmd.lower()
        if any(pattern in lower for pattern in _DANGEROUS_PATTERNS):
            print(f"⚠️  Unsafe command blocked: {cmd}")
        else:
            safe.append(cmd)
    return safe