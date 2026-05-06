from fastapi import APIRouter, HTTPException

from repositories.ticket_repository import (
    get_all_tickets,
    search_completed_tickets_with_rca,
    update_ticket_rca,
)
from services.embedding_service import get_embedding
from modules.copilot_rca.handler import handle_rca_flow
from modules.copilot_rca.service import get_confidence_label, get_rca_summary

router = APIRouter()


@router.get("/tickets/{issueKey}/rca")
async def get_rca(issueKey: str):
    try:
        # ── 1. Find the ticket ──
        tickets = await get_all_tickets()
        ticket  = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {issueKey} not found")

        # ── 2. Block RCA on child/duplicate tickets ──
        if ticket.get("parent_ticket_key"):
            raise HTTPException(
                status_code=400,
                detail="RCA is only available on parent tickets"
            )

        # ── 3. Return cached result if already computed ──
        if ticket.get("rca_root_cause"):
            confidence = ticket.get("rca_confidence", "LOW")
            affected   = ticket.get("rca_affected", "Unknown")
            print(f"📦 [{issueKey}] CACHE HIT — returning stored RCA (no LLM call)")
            return {
                "root_cause":       ticket.get("rca_root_cause"),
                "affected":         affected,
                "steps":            ticket.get("rca_steps", []),
                "confidence":       confidence,
                "confidence_label": get_confidence_label(confidence),
                "summary":          get_rca_summary(confidence, affected),
                "cached":           True,
            }

        # ── 4. Validate description ──
        summary     = ticket.get("summary", "")
        description = ticket.get("description", "")

        if not description:
            raise HTTPException(
                status_code=400,
                detail="Ticket has no description — RCA requires description"
            )

        # ── 5. Vector search on completed parent tickets with RCA ──
        similar_past = []
        query_embedding = await get_embedding(f"{summary} {description}")

        if query_embedding:
            query_embedding = [float(x) for x in query_embedding]
            matches = await search_completed_tickets_with_rca(query_embedding, top_k=3)
            similar_past = [
                t for t in matches
                if t.get("issue_key") != issueKey
            ]
            print(f"[RCA] {len(similar_past)} similar completed tickets found")

        # ── 6. Build state ──
        state = {
            "id":           issueKey,
            "summary":      summary,
            "data":         ticket,
            "type":         None,
            "message":      "",
            "similar_past": similar_past,
        }

        # ── 7. Run RCA handler ──
        # If similar_past → LLM picks best match → returns that ticket's RCA columns
        # If no similar_past → LLM generates fresh RCA
        if similar_past:
            print(f"🔍 [{issueKey}] {len(similar_past)} candidates — LLM picking best match...")
        else:
            print(f"🤖 [{issueKey}] No similar tickets — LLM generating fresh RCA...")

        result = await handle_rca_flow(state)

        if result.get("type") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        # ── 8. Always persist ──
        await update_ticket_rca(
            issue_key          = issueKey,
            root_cause         = result.get("rca_root_cause"),
            affected_component = result.get("rca_affected"),
            resolution_steps   = result.get("rca_steps", []),
            confidence         = result.get("rca_confidence"),
        )
        print(f"💾 [{issueKey}] RCA saved — future requests will use cache")

        # ── 9. Return result ──
        return {
            "root_cause":       result.get("rca_root_cause"),
            "affected":         result.get("rca_affected"),
            "steps":            result.get("rca_steps", []),
            "confidence":       result.get("rca_confidence"),
            "confidence_label": result.get("rca_confidence_label"),
            "summary":          result.get("rca_summary"),
            "cached":           False,
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ get_rca error: {e}")
        raise HTTPException(status_code=500, detail=str(e))