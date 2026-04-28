from core.constants import SIMILARITY_THRESHOLD
from modules.duplicate_detection.agent import find_best_match
from modules.duplicate_detection.service import generate_related

from services.jira_service import (
    create_ticket,
    generate_child_id,
    append_duplicate
)

from repositories.ticket_repository import (
    get_all_tickets,
    insert_ticket
)


# ───────────── MAIN FLOW ONLY ─────────────
async def handle_duplicate_flow(state):

    summary = state.get("summary", "")

    if not summary:
        return {"type": "error", "message": "Summary required"}

    tickets = await get_all_tickets()
    score, parent = await find_best_match(summary, tickets or [])

    # ───────────── DUPLICATE ─────────────
    if parent and score >= SIMILARITY_THRESHOLD:

        parent_key = parent.get("issue_key")

        child_id = await generate_child_id(parent_key)

        await append_duplicate(parent_key, child_id, summary)

        await insert_ticket({
            "issue_key": child_id,
            "summary": summary,
            "status": "Duplicate",
            "is_duplicate": True,
            "parent_ticket_key": parent_key
        })

        return {
            "type": "duplicate",
            "id": child_id,
            "score": score
        }

    # ───────────── UNIQUE ─────────────
    related = await generate_related(summary)

    data = state.get("data")

    new_ticket = await create_ticket(data, related)

    issue_key = new_ticket.get("issueKey")

    await insert_ticket({
        "issue_key": issue_key,
        "summary": summary,
        "status": "Open",
        "is_duplicate": False,
        "parent_ticket_key": None
    })

    return {
        "type": "new",
        "id": issue_key,
        "score": score
    }