import re
from services.llm_service import call_llm
from .prompt import DUPLICATE_PROMPT, RELATED_PROMPT


# Extract numeric similarity score from LLM response (0–100)
def extract_score(text: str) -> int:
    if not text:
        return 0

    text = text.strip()

    match = re.search(r"\b(\d{1,3})\b", text)
    if not match:
        return 0

    return min(max(int(match.group(1)), 0), 100)


# Get similarity score between two ticket summaries using LLM
async def get_similarity(new, existing):
    prompt = DUPLICATE_PROMPT.format(new=new, existing=existing)

    res = await call_llm(prompt)

    return extract_score(res)


# Generate related issue suggestions from LLM output
async def generate_related(summary):
    prompt = RELATED_PROMPT.format(summary=summary)

    res = await call_llm(prompt)

    # Convert LLM response into clean list of items
    return [
        line.strip("-• \n")
        for line in res.split("\n")
        if line.strip()
    ]