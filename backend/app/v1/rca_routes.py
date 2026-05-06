from fastapi import APIRouter, HTTPException

from core.constants import RCA_SIMILARITY_THRESHOLD
from repositories.ticket_repository import (
    get_all_tickets,
    search_completed_tickets_with_rca,
    update_ticket_rca,
)
from services.embedding_service import get_embedding
from modules.copilot_rca.agent import is_same_issue
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
                "root_cause":        ticket.get("rca_root_cause"),
                "affected":          affected,
                "steps":             ticket.get("rca_steps", []),
                "confidence":        confidence,
                "confidence_label":  get_confidence_label(confidence),
                "summary":           get_rca_summary(confidence, affected),
                "source":            ticket.get("rca_source"),
                "matched_from":      ticket.get("rca_matched_from"),
                "matched_summary":   ticket.get("rca_matched_summary"),
                "cached":            True,
            }

        # ── 4. Validate description ──
        summary     = ticket.get("summary", "")
        description = ticket.get("description", "")

        if not description:
            raise HTTPException(
                status_code=400,
                detail="Ticket has no description — RCA requires description"
            )

        # ── 5. Embed current ticket ──
        query_embedding = await get_embedding(f"{summary} {description}")

        # ── 6. Vector search → top completed parent tickets with RCA ──
        best = None
        if query_embedding:
            query_embedding = [float(x) for x in query_embedding]
            matches = await search_completed_tickets_with_rca(query_embedding, top_k=5)

            # Exclude self, take top result (already sorted by similarity desc)
            candidates = [t for t in matches if t.get("issue_key") != issueKey]

            if candidates:
                top        = candidates[0]
                similarity = top.get("similarity", 0)

                print(f"[RCA] Top match: '{top.get('issue_key')}' similarity={similarity:.3f} threshold={RCA_SIMILARITY_THRESHOLD}")

                if similarity >= RCA_SIMILARITY_THRESHOLD:
                    print(f"🔍 [{issueKey}] Above threshold — asking LLM: is this the same issue?")
                    current = {"summary": summary, "description": description}
                    same, confidence = is_same_issue(current, top)

                    if same:
                        best = top
                        best["match_confidence"] = confidence
                        print(f"✅ [{issueKey}] LLM CALL 1 — confirmed same issue — copying RCA from '{top.get('issue_key')}' (no generation needed)")
                    else:
                        print(f"⚠️  [{issueKey}] LLM CALL 1 — confirmed DIFFERENT issue — falling through to fresh generation")
                else:
                    print(f"🚫 [{issueKey}] Below threshold ({similarity:.3f} < {RCA_SIMILARITY_THRESHOLD}) — skipping LLM match check — going straight to fresh generation")
            else:
                print(f"📭 [{issueKey}] No completed parent tickets found in vector search — going straight to fresh generation")

        # ── 7A. High similarity match — copy RCA directly, no LLM ──
        if best:
            confidence = best.get("rca_confidence", "LOW")
            affected   = best.get("rca_affected", "Unknown")

            await update_ticket_rca(
                issue_key        = issueKey,
                root_cause       = best.get("rca_root_cause"),
                affected_component = affected,
                resolution_steps = best.get("rca_steps", []),
                confidence       = confidence,
                source           = "matched",
                matched_from     = best.get("issue_key"),
                matched_summary  = best.get("summary"),
            )
            print(f"💾 [{issueKey}] Matched RCA saved from '{best.get('issue_key')}'")

            return {
                "root_cause":       best.get("rca_root_cause"),
                "affected":         affected,
                "steps":            best.get("rca_steps", []),
                "confidence":       confidence,
                "confidence_label": get_confidence_label(confidence),
                "summary":          get_rca_summary(confidence, affected),
                "source":           "matched",
                "matched_from":     best.get("issue_key"),
                "matched_summary":  best.get("summary"),
                "cached":           False,
            }

        # ── 7B. Below threshold or no matches — generate fresh RCA via LLM ──
        print(f"🤖 [{issueKey}] LLM CALL — generating fresh RCA (source: {'different issue' if candidates else 'no past tickets found'})")
        state = {
            "id":      issueKey,
            "summary": summary,
            "data":    ticket,
            "type":    None,
            "message": "",
        }

        result = await handle_rca_flow(state)

        if result.get("type") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        await update_ticket_rca(
            issue_key          = issueKey,
            root_cause         = result.get("rca_root_cause"),
            affected_component = result.get("rca_affected"),
            resolution_steps   = result.get("rca_steps", []),
            confidence         = result.get("rca_confidence"),
            source             = "generated",
            matched_from       = None,
            matched_summary    = None,
        )
        print(f"💾 [{issueKey}] Fresh RCA saved")

        return {
            "root_cause":       result.get("rca_root_cause"),
            "affected":         result.get("rca_affected"),
            "steps":            result.get("rca_steps", []),
            "confidence":       result.get("rca_confidence"),
            "confidence_label": result.get("rca_confidence_label"),
            "summary":          result.get("rca_summary"),
            "source":           "generated",
            "matched_from":     None,
            "matched_summary":  None,
            "cached":           False,
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ get_rca error: {e}")
        raise HTTPException(status_code=500, detail=str(e))