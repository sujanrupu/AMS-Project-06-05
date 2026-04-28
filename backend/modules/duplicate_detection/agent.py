import re
from services.llm_service import call_llm
from .prompt import DUPLICATE_PROMPT, RELATED_PROMPT


# ───────────── CLEAN LLM SCORE PARSER ─────────────
def parse_score(text: str) -> int:
    if not text:
        return 0

    match = re.search(r"\b(\d{1,3})\b", text.strip())

    if not match:
        return 0

    score = int(match.group(1))

    return max(0, min(score, 100))


# ───────────── SIMILARITY CHECK ─────────────
async def get_similarity(new: str, existing: str) -> int:
    prompt = DUPLICATE_PROMPT.format(new=new, existing=existing)

    try:
        res = await call_llm(prompt)
        return parse_score(res)
    except Exception:
        return 0


# ───────────── BEST MATCH FINDER ─────────────
async def find_best_match(summary, tickets):
    best_score = 0
    best_ticket = None

    if not tickets:
        return 0, None

    for t in tickets:
        existing_summary = t.get("summary", "")

        score = await get_similarity(summary, existing_summary)

        # 🔥 IMPORTANT FILTER (prevents false duplicates)
        if score >= best_score and score >= 60:
            best_score = score
            best_ticket = t

    # final safety check
    if best_score < 60:
        return 0, None

    return best_score, best_ticket


# ───────────── RELATED ISSUES ─────────────
async def generate_related(summary: str):
    prompt = RELATED_PROMPT.format(summary=summary)

    try:
        return await call_llm(prompt)
    except Exception:
        return ""