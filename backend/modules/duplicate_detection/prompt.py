DUPLICATE_PROMPT = """
You are a strict similarity scoring engine.

Compare the two issues and return ONLY a single integer score between 0 and 100.

RULES:
- Output ONLY a number (no text, no %, no explanation)
- 70–100 → highly similar (likely duplicates)
- 40–69 → partially related
- 0–39 → unrelated

New issue:
{new}

Existing issue:
{existing}

Output example:
85
"""

RELATED_PROMPT = """
Generate 4 short related issue titles.

Input:
{summary}

Rules:
- Only bullet points
- Only titles (no description)
- Each line should be a potential issue topic

Output format:
- Issue 1
- Issue 2
- Issue 3
- Issue 4
"""