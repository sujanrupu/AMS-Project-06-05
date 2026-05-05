PRIORITY_MATRIX = {
    ("High", "High"): "P1",
    ("High", "Medium"): "P2",
    ("High", "Low"): "P3",
    ("Medium", "High"): "P2",
    ("Medium", "Medium"): "P3",
    ("Medium", "Low"): "P4",
    ("Low", "High"): "P3",
    ("Low", "Medium"): "P4",
    ("Low", "Low"): "P5",
}

PRIORITY_LABEL = {
    "P1": "Critical",
    "P2": "High",
    "P3": "Medium",
    "P4": "Low",
    "P5": "Planning"
}

SLA_RULES = {
    "P1": {"response_time": "15 minutes", "resolution_time": "4 hours"},
    "P2": {"response_time": "30 minutes", "resolution_time": "8 hours"},
    "P3": {"response_time": "4 hours", "resolution_time": "16 hours"},
    "P4": {"response_time": "8 hours", "resolution_time": "24 hours"},
    "P5": {"response_time": "16 hours", "resolution_time": "48 hours"},
}

VALID = {"High", "Medium", "Low"}


# ─────────────────────────────────────────────
# FIXED NORMALIZATION (ROBUST NLP SAFE)
# ─────────────────────────────────────────────
def normalize(value):
    try:
        if not value:
            return "Medium"

        value = str(value).strip().lower()

        # extract meaning instead of strict match
        if "high" in value:
            return "High"
        if "medium" in value:
            return "Medium"
        if "low" in value:
            return "Low"

        return "Medium"

    except Exception:
        return "Medium"


# ─────────────────────────────────────────────
# PRIORITY MAPPING
# ─────────────────────────────────────────────
def map_priority(urgency, impact):
    try:
        key = (
            normalize(urgency),
            normalize(impact)
        )

        return PRIORITY_MATRIX.get(key, "P5")

    except Exception:
        return "P5"


# ─────────────────────────────────────────────
# LABEL
# ─────────────────────────────────────────────
def get_label(priority):
    return PRIORITY_LABEL.get(priority, "Planning")


# ─────────────────────────────────────────────
# SLA
# ─────────────────────────────────────────────
def get_sla(priority):
    return SLA_RULES.get(priority, SLA_RULES["P5"])