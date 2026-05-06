import os
import json
import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from .prompt import GENERATE_PROMPT, SAME_ISSUE_PROMPT

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


def is_same_issue(current: dict, past: dict) -> tuple[bool, str]:
    """
    LLM decides if current incident is the same type as the past one.
    Returns (is_same: bool, confidence: str)
    """
    prompt = SAME_ISSUE_PROMPT.format(
        summary=current.get("summary", ""),
        description=current.get("description", ""),
        past_summary=past.get("summary", ""),
        past_description=past.get("description", ""),
        past_root_cause=past.get("rca_root_cause", ""),
        past_affected=past.get("rca_affected", ""),
    )

    try:
        response = llm.invoke(prompt)
        raw      = _clean_llm_output(response.content)
        result   = json.loads(raw)

        same       = bool(result.get("is_same_issue", False))
        confidence = str(result.get("confidence", "LOW")).upper()
        reason     = result.get("reason", "")

        print(f"[RCAAgent] Same issue: {same} | Confidence: {confidence} | Reason: {reason}")
        return same, confidence

    except Exception as e:
        print(f"[RCAAgent] is_same_issue failed: {e}")
        return False, "LOW"


def generate_fresh_rca(current: dict) -> dict:
    """
    LLM generates a brand new RCA when no similar past tickets exist
    or past ticket is a different issue.
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