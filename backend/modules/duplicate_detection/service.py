import re
from services.llm_service import call_llm
from .prompt import DUPLICATE_PROMPT, RELATED_PROMPT


# ───────────── SCORE PARSER ─────────────
def extract_score(text: str) -> int:
    if not text:
        return 0

    text = text.strip()

    match = re.search(r"\b(\d{1,3})\b", text)
    if not match:
        return 0

    return min(max(int(match.group(1)), 0), 100)


# ───────────── SIMILARITY ─────────────
async def get_similarity(new, existing):
    prompt = DUPLICATE_PROMPT.format(new=new, existing=existing)

    res = await call_llm(prompt)

    return extract_score(res)


# ───────────── RELATED ISSUES ─────────────
async def generate_related(summary):
    prompt = RELATED_PROMPT.format(summary=summary)

    res = await call_llm(prompt)

    return [
        line.strip("-• \n")
        for line in res.split("\n")
        if line.strip()
    ]
