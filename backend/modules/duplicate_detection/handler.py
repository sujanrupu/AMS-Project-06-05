# modules/duplicate_detection/handler.py

from core.constants import SIMILARITY_THRESHOLD
from modules.duplicate_detection.agent import find_best_match
from modules.duplicate_detection.service import generate_related

from services.jira_service import (
    create_ticket,
    generate_child_id,
    append_duplicate
)

from services.embedding_service import get_embedding

from repositories.ticket_repository import (
    get_all_tickets,
    insert_ticket,
    search_similar_tickets
)


# ─────────────────────────────────────────────
# DUPLICATE DETECTION FLOW
# ─────────────────────────────────────────────
async def handle_duplicate_flow(state):

    data    = state.get("data") or {}
    summary = state.get("summary", "")

    # ─────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────
    if not data or not summary:
        return {
            **state,
            "type":    "error",
            "message": "Invalid request payload"
        }

    # safe extraction — supports both object and dict
    name        = getattr(data, "name",        None) or data.get("name",        "")
    email       = getattr(data, "email",       None) or data.get("email",       "")
    description = getattr(data, "description", None) or data.get("description", "")

    # ─────────────────────────────────────────────
    # STEP 1 — VECTOR SEARCH (OPEN TICKETS ONLY)
    # ─────────────────────────────────────────────
    candidate_tickets = []

    query_embedding = await get_embedding(summary)

    if query_embedding:
        query_embedding = [float(x) for x in query_embedding]

        candidate_tickets = await search_similar_tickets(
            query_embedding,
            top_k=5
        )

        # Only consider open tickets for duplicate detection
        candidate_tickets = [
            t for t in candidate_tickets
            if t.get("status") == "Open"
        ]

    # ─────────────────────────────────────────────
    # FALLBACK — ALL OPEN TICKETS IF VECTOR EMPTY
    # ─────────────────────────────────────────────
    if not candidate_tickets:
        tickets = await get_all_tickets() or []

        candidate_tickets = [
            t for t in tickets
            if t.get("status") == "Open"
        ]

    # ─────────────────────────────────────────────
    # STEP 2 — LLM SIMILARITY CHECK
    # ─────────────────────────────────────────────
    score, parent = await find_best_match(summary, candidate_tickets)

    # ─────────────────────────────────────────────
    # DUPLICATE FLOW
    # ─────────────────────────────────────────────
    if parent and score >= SIMILARITY_THRESHOLD:

        parent_key = parent.get("parent_ticket_key") or parent.get("issue_key")

        child_id = await generate_child_id(parent_key)

        await append_duplicate(parent_key, child_id, summary)

        await insert_ticket({
            "issue_key":         child_id,
            "name":              name,
            "email":             email,
            "summary":           summary,
            "description":       description,
            "status":            "Open",
            "is_duplicate":      True,
            "parent_ticket_key": parent_key,

            # No SLA / priority inheritance for duplicates
            "priority":              None,
            "priority_label":        None,
            "sla_response_time":     None,
            "sla_resolution_time":   None,

            # No embedding for duplicates
            "embedding": None
        })

        # Propagate duplicate state through pipeline
        return {
            **state,
            "type":         "success",
            "message":      "Duplicate ticket linked successfully",
            "id":           child_id,
            "is_duplicate": True
        }

    # ─────────────────────────────────────────────
    # NEW TICKET FLOW
    # ─────────────────────────────────────────────
    related = await generate_related(summary)

    new_ticket = await create_ticket(data, related)

    issue_key = new_ticket.get("issueKey") if new_ticket else None

    if not issue_key:
        return {
            **state,
            "type":    "error",
            "message": "Failed to create Jira ticket"
        }

    # ─────────────────────────────────────────────
    # STEP 3 — GENERATE EMBEDDING FOR PARENT
    # ─────────────────────────────────────────────
    embedding = await get_embedding(f"{summary}\n{related}")

    if embedding:
        embedding = [float(x) for x in embedding]

    # ─────────────────────────────────────────────
    # STORE IN SUPABASE
    # ─────────────────────────────────────────────
    await insert_ticket({
        "issue_key":         issue_key,
        "name":              name,
        "email":             email,
        "summary":           summary,
        "description":       description,
        "status":            "Open",
        "is_duplicate":      False,
        "parent_ticket_key": None,
        "embedding":         embedding
    })

    return {
        **state,
        "type":         "success",
        "message":      "Ticket registered successfully",
        "id":           issue_key,
        "is_duplicate": False
    }