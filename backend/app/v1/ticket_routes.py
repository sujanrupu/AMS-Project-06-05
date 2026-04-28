from fastapi import APIRouter

from schemas.ticket_schema import TicketRequest
from orchestrator.ams_orchestrator import handle_ticket

from repositories.ticket_repository import (
    get_all_tickets,
    delete_ticket
)

from services.jira_service import delete_jira_ticket

from modules.duplicate_detection.handler import handle_duplicate_flow


router = APIRouter()


# ───────────── SUBMIT ─────────────
@router.post("/submit")
async def submit(data: TicketRequest):
    """
    Main ticket submission endpoint
    """

    result = await handle_ticket(data)

    # safe fallback (never break frontend)
    if not isinstance(result, dict):
        return {
            "type": "error",
            "message": "Invalid orchestrator response"
        }

    return result


# ───────────── GET TICKETS ─────────────
@router.get("/tickets")
async def get_tickets():
    """
    Always return list (frontend-safe)
    """

    tickets = await get_all_tickets()

    if not isinstance(tickets, list):
        return []

    return tickets


# ───────────── DELETE TICKET ─────────────
@router.delete("/tickets/{issueKey}")
async def delete(issueKey: str):
    """
    Deletes from Jira + DB
    """

    try:
        jira_deleted = await delete_jira_ticket(issueKey)

        if not jira_deleted:
            return {
                "type": "error",
                "message": f"Failed to delete {issueKey} from Jira"
            }

        await delete_ticket(issueKey)

        return {
            "type": "success",
            "message": f"{issueKey} deleted successfully"
        }

    except Exception as e:
        return {
            "type": "error",
            "message": str(e)
        }