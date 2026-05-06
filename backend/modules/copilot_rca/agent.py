import os
import json
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from .prompt import MATCH_PROMPT, GENERATE_PROMPT

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in environment")

llm = ChatGroq(api_key=GROQ_API_KEY, model_name=MODEL_NAME)


def _clean_llm_output(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$",          "", raw).strip()
    return raw


def pick_best_match(current: dict, candidates: list) -> dict | None:
    """
    LLM picks the best matching past ticket from candidates.
    Returns matched ticket dict or None if no meaningful match.
    """
    formatted = ""
    for i, t in enumerate(candidates):
        formatted += (
            f"\nCandidate {i}:\n"
            f"  Summary: {t.get('summary', 'N/A')}\n"
            f"  Description: {t.get('description', 'N/A')}\n"
            f"  Root Cause: {t.get('rca_root_cause', 'N/A')}\n"
            f"  Affected: {t.get('rca_affected', 'N/A')}\n"
            f"  Resolution: {' | '.join(t.get('rca_steps', []) or [])}\n"
        )

    prompt = MATCH_PROMPT.format(
        summary=current.get("summary", ""),
        description=current.get("description", ""),
        candidates=formatted,
        count=len(candidates) - 1,
    )

    try:
        response = llm.invoke(prompt)
        raw      = _clean_llm_output(response.content)
        result   = json.loads(raw)

        if result.get("no_match"):
            return None

        index = result.get("best_match_index")
        if not isinstance(index, int) or index < 0 or index >= len(candidates):
            return None

        matched = candidates[index]
        matched["rca_confidence"] = str(result.get("confidence", "LOW")).upper()
        return matched

    except Exception as e:
        print(f"[RCAAgent] pick_best_match failed: {e}")
        return None


def generate_fresh_rca(current: dict) -> dict:
    """
    LLM generates a brand new RCA when no similar past tickets exist.
    """
    prompt = GENERATE_PROMPT.format(
        summary=current.get("summary", ""),
        description=current.get("description", ""),
    )

    try:
        response = llm.invoke(prompt)
        raw      = _clean_llm_output(response.content)
        result   = json.loads(raw)

        required = ("root_cause", "affected_component", "resolution_steps", "confidence")
        if not all(k in result for k in required):
            raise ValueError("Missing required keys in LLM response")

        confidence = str(result["confidence"]).upper().strip()
        if confidence not in ("HIGH", "MEDIUM", "LOW"):
            confidence = "LOW"

        resolution_steps = result["resolution_steps"]
        if not isinstance(resolution_steps, list) or not resolution_steps:
            resolution_steps = ["Review incident manually — LLM returned no steps."]

        return {
            "status":             "success",
            "root_cause":         str(result["root_cause"]).strip(),
            "affected_component": str(result["affected_component"]).strip(),
            "resolution_steps":   resolution_steps,
            "confidence":         confidence,
        }

    except Exception as e:
        print(f"[RCAAgent] generate_fresh_rca failed: {e}")
        return {
            "status":             "error",
            "root_cause":         f"RCA generation failed: {str(e)[:60]}",
            "affected_component": "Unknown",
            "resolution_steps":   ["Escalate to L3 engineering for manual investigation."],
            "confidence":         "LOW",
        }