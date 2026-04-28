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

    data = state.get("data")
    summary = state.get("summary", "")

    if not data or not summary:
        return {
            "type": "error",
            "message": "Invalid request payload"
        }

    # 🔹 STEP 1: GET ALL TICKETS
    tickets = await get_all_tickets() or []

    # 🔹 STEP 2: FILTER ONLY OPEN TICKETS
    open_tickets = [
        t for t in tickets
        if t.get("status") == "Open"
    ]

    # 🔹 STEP 3: RUN SIMILARITY ONLY ON OPEN TICKETS
    score, parent = await find_best_match(summary, open_tickets)

    # ───────────── DUPLICATE FLOW ─────────────
    if parent and score >= SIMILARITY_THRESHOLD:

        # 🔥 ALWAYS RESOLVE ROOT PARENT
        parent_key = parent.get("parent_ticket_key") or parent.get("issue_key")

        # 🔥 generate next child under ROOT parent
        child_id = await generate_child_id(parent_key)

        await append_duplicate(parent_key, child_id, summary)

        await insert_ticket({
            "issue_key": child_id,
            "name": data.name,
            "email": data.email,
            "summary": summary,
            "description": data.description,

            # ✅ FIXED (CRITICAL)
            "status": "Open",          # 🔥 SAME as parent
            "is_duplicate": True,      # 🔥 mark duplicate properly

            "parent_ticket_key": parent_key
        })

        return {
            "type": "success",
            "message": "Duplicate ticket linked successfully",
            "id": child_id
        }

    # ───────────── NEW TICKET FLOW ─────────────
    related = await generate_related(summary)

    new_ticket = await create_ticket(data, related)

    issue_key = new_ticket.get("issueKey")

    if not issue_key:
        return {
            "type": "error",
            "message": "Failed to create Jira ticket"
        }

    await insert_ticket({
        "issue_key": issue_key,
        "name": data.name,
        "email": data.email,
        "summary": summary,
        "description": data.description,
        "status": "Open",
        "is_duplicate": False,
        "parent_ticket_key": None
    })

    return {
        "type": "success",
        "message": "Ticket registered successfully",
        "id": issue_key
    }