from core.constants import SIMILARITY_THRESHOLD
from modules.duplicate_detection.agent import find_best_match
from modules.duplicate_detection.service import generate_related

from services.jira_service import (
    create_ticket,
    generate_child_id,
    append_duplicate
)

from services.embedding_service import get_embedding  # ✅ NEW

from repositories.ticket_repository import (
    get_all_tickets,
    insert_ticket,
    search_similar_tickets   # ✅ NEW
)


# Main duplicate detection and ticket routing flow
async def handle_duplicate_flow(state):

    data = state.get("data")
    summary = state.get("summary", "")

    # Validate input payload
    if not data or not summary:
        return {
            "type": "error",
            "message": "Invalid request payload"
        }

    # ─────────────────────────────────────────────
    # 🔥 STEP 1: VECTOR SEARCH (NEW)
    # ─────────────────────────────────────────────
    candidate_tickets = []

    query_embedding = await get_embedding(summary)

    if query_embedding:
        # ensure correct format
        query_embedding = [float(x) for x in query_embedding]

        candidate_tickets = await search_similar_tickets(
            query_embedding,
            top_k=5
        )

    # ─────────────────────────────────────────────
    # ⚠️ FALLBACK (IMPORTANT)
    # ─────────────────────────────────────────────
    if not candidate_tickets:
        tickets = await get_all_tickets() or []

        candidate_tickets = [
            t for t in tickets
            if t.get("status") == "Open"
        ]

    # ─────────────────────────────────────────────
    # 🔍 STEP 2: LLM SIMILARITY (UNCHANGED)
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
            "issue_key": child_id,
            "name": data.name,
            "email": data.email,
            "summary": summary,
            "description": data.description,
            "status": "Open",
            "is_duplicate": True,
            "parent_ticket_key": parent_key,
            "embedding": None   # ❌ IMPORTANT (no embedding for duplicates)
        })

        return {
            "type": "success",
            "message": "Duplicate ticket linked successfully",
            "id": child_id
        }

    # ─────────────────────────────────────────────
    # NEW TICKET FLOW
    # ─────────────────────────────────────────────
    related = await generate_related(summary)

    new_ticket = await create_ticket(data, related)

    issue_key = new_ticket.get("issueKey") if new_ticket else None

    if not issue_key:
        return {
            "type": "error",
            "message": "Failed to create Jira ticket"
        }

    # ─────────────────────────────────────────────
    # 🔥 STEP 3: CREATE EMBEDDING FOR PARENT
    # ─────────────────────────────────────────────
    embedding = await get_embedding(f"{summary}\n{related}")

    if embedding:
        embedding = [float(x) for x in embedding]

    # Store new ticket in DB
    await insert_ticket({
        "issue_key": issue_key,
        "name": data.name,
        "email": data.email,
        "summary": summary,
        "description": data.description,
        "status": "Open",
        "is_duplicate": False,
        "parent_ticket_key": None,
        "embedding": embedding   
    })

    return {
        "type": "success",
        "message": "Ticket registered successfully",
        "id": issue_key
    }