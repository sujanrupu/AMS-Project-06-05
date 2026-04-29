from fastapi import APIRouter

# schemas + orchestrator layer
from schemas.ticket_schema import TicketRequest
from orchestrator.ams_orchestrator import handle_ticket

# repository layer (DB operations)
from repositories.ticket_repository import (
    get_all_tickets,
    delete_ticket_cascade,
    update_status_cascade
)

# Jira integration services
from services.jira_service import (
    delete_jira_ticket,
    update_jira_status
)

# FastAPI router instance
router = APIRouter()


# ───────────── SUBMIT TICKET ─────────────
@router.post("/submit")
async def submit(data: TicketRequest):
    # Handles full ticket creation pipeline via orchestrator
    result = await handle_ticket(data)

    # Ensure frontend always gets dict response
    if not isinstance(result, dict):
        return {
            "type": "error",
            "message": "Invalid orchestrator response"
        }

    return result


# ───────────── GET ALL TICKETS ─────────────
@router.get("/tickets")
async def get_tickets():
    # Fetch all tickets from DB
    tickets = await get_all_tickets()

    # Ensure safe frontend response
    if not isinstance(tickets, list):
        return []

    return tickets


# ───────────── DELETE TICKET (CASCADE) ─────────────
@router.delete("/tickets/{issueKey}")
async def delete(issueKey: str):
    try:
        # Delete parent ticket from Jira only
        jira_deleted = await delete_jira_ticket(issueKey)

        if not jira_deleted:
            return {
                "type": "error",
                "message": f"Failed to delete {issueKey} from Jira"
            }

        # Delete parent + child tickets from DB
        db_deleted = await delete_ticket_cascade(issueKey)

        if not db_deleted:
            return {
                "type": "error",
                "message": "Database delete failed"
            }

        return {
            "type": "success",
            "message": "Parent and all child tickets deleted successfully"
        }

    except Exception as e:
        print("❌ delete error:", str(e))
        return {
            "type": "error",
            "message": str(e)
        }


# ───────────── COMPLETE TICKET ─────────────
@router.put("/tickets/{issueKey}/complete")
async def complete_ticket(issueKey: str):
    try:
        tickets = await get_all_tickets()

        # no data safety check
        if not tickets:
            return {"type": "error", "message": "No tickets found"}

        # find selected ticket
        current = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not current:
            return {"type": "error", "message": "Ticket not found"}

        # resolve root parent (parent or self)
        parent_key = current.get("parent_ticket_key") or current.get("issue_key")

        print(f"🔍 Completing parent ticket: {parent_key}")

        # update Jira only for parent ticket
        jira_ok = await update_jira_status(parent_key)

        if not jira_ok:
            print(f"⚠️ Jira update failed for parent: {parent_key}")

        # update DB for parent + children
        db_ok = await update_status_cascade(parent_key, "Completed")

        if not db_ok:
            return {
                "type": "error",
                "message": "Database update failed"
            }

        print(f"✅ Completed status applied for {parent_key}")

        return {
            "type": "success",
            "message": "Marked as completed",
            "id": parent_key
        }

    except Exception as e:
        print("❌ complete_ticket error:", str(e))
        return {
            "type": "error",
            "message": str(e)
        }