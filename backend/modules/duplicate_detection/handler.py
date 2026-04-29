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

    # Fetch all tickets from DB
    tickets = await get_all_tickets() or []

    # Filter only open tickets for duplicate check
    open_tickets = [
        t for t in tickets
        if t.get("status") == "Open"
    ]

    # Run similarity check only on open tickets
    score, parent = await find_best_match(summary, open_tickets)

    # Duplicate ticket flow
    if parent and score >= SIMILARITY_THRESHOLD:

        # Resolve root parent ticket
        parent_key = parent.get("parent_ticket_key") or parent.get("issue_key")

        # Generate child ticket ID under root parent
        child_id = await generate_child_id(parent_key)

        # Log duplicate relationship in Jira
        await append_duplicate(parent_key, child_id, summary)

        # Store duplicate ticket in DB
        await insert_ticket({
            "issue_key": child_id,
            "name": data.name,
            "email": data.email,
            "summary": summary,
            "description": data.description,
            "status": "Open",          # keep same lifecycle state
            "is_duplicate": True,      # mark as duplicate
            "parent_ticket_key": parent_key
        })

        return {
            "type": "success",
            "message": "Duplicate ticket linked successfully",
            "id": child_id
        }

    # New ticket flow (no duplicate found)
    related = await generate_related(summary)

    new_ticket = await create_ticket(data, related)

    issue_key = new_ticket.get("issueKey")

    # Validate Jira ticket creation
    if not issue_key:
        return {
            "type": "error",
            "message": "Failed to create Jira ticket"
        }

    # Store new ticket in DB
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