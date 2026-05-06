CONFIDENCE_LABEL = {
    "HIGH":   "High Confidence — Root cause clearly identified",
    "MEDIUM": "Medium Confidence — Root cause inferred, verify before action",
    "LOW":    "Low Confidence — Insufficient data, manual review required",
}


def get_confidence_label(confidence: str) -> str:
    return CONFIDENCE_LABEL.get(str(confidence).upper(), "Unknown Confidence")


def normalize_text(text) -> str:
    if not text or not isinstance(text, str):
        return ""
    return text.lower().strip()


def get_rca_summary(confidence: str, affected_component: str) -> str:
    messages = {
        "HIGH":   f"✅ Root cause identified with high confidence in: {affected_component}",
        "MEDIUM": f"⚠️  Root cause inferred — please verify in: {affected_component}",
        "LOW":    f"🔍 Root cause unclear — manual investigation needed for: {affected_component}",
    }
    return messages.get(str(confidence).upper(), "RCA analysis complete")