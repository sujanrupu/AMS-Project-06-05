import re
import asyncio

from services.llm_service import call_llm
from core.constants import SIMILARITY_THRESHOLD  
from .prompt import DUPLICATE_PROMPT, RELATED_PROMPT


# ─────────────────────────────────────────────
# PARSE SCORE
# ─────────────────────────────────────────────
def parse_score(text: str) -> int:
    if not text:
        return 0

    match = re.search(r"\b(\d{1,3})\b", text.strip())

    if not match:
        return 0

    score = int(match.group(1))
    return max(0, min(score, 100))


# ─────────────────────────────────────────────
# LLM SIMILARITY
# ─────────────────────────────────────────────
async def get_similarity(new: str, existing: str) -> int:
    prompt = DUPLICATE_PROMPT.format(new=new, existing=existing)

    try:
        res = await call_llm(prompt)
        return parse_score(res)
    except Exception:
        return 0


# ─────────────────────────────────────────────
# FIND BEST MATCH (PARALLEL VERSION)
# ─────────────────────────────────────────────
async def find_best_match(summary, tickets):

    if not tickets:
        return 0, None

    # Run all similarity checks in parallel
    tasks = [
        get_similarity(summary, t.get("summary", ""))
        for t in tickets
    ]

    scores = await asyncio.gather(*tasks)

    best_score = 0
    best_ticket = None

    for i, score in enumerate(scores):
        if score >= best_score and score >= SIMILARITY_THRESHOLD:
            best_score = score
            best_ticket = tickets[i]

    if best_score < SIMILARITY_THRESHOLD:
        return 0, None

    return best_score, best_ticket


# ─────────────────────────────────────────────
# RELATED ISSUES
# ─────────────────────────────────────────────
async def generate_related(summary: str):
    prompt = RELATED_PROMPT.format(summary=summary)

    try:
        return await call_llm(prompt)
    except Exception:
        return ""