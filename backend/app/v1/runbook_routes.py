# app/v1/runbook_routes.py

from fastapi import APIRouter, HTTPException

from repositories.ticket_repository import (
    get_all_tickets,
    update_ticket_runbook,
)
from repositories.runbook_repository import insert_runbook
from modules.runbook_execution.handler import handle_runbook_flow
from services.embedding_service import get_embedding
from services.slack_service import send_to_slack

router = APIRouter()


# ───────────── GET RUNBOOK FOR TICKET ─────────────
@router.get("/tickets/{issueKey}/runbook")
async def get_runbook(issueKey: str):
    try:
        tickets = await get_all_tickets()
        ticket  = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {issueKey} not found")

        # ── child ticket → redirect to parent ──
        if ticket.get("is_duplicate") and ticket.get("parent_ticket_key"):
            parent_key = ticket["parent_ticket_key"]
            print(f"↩️  [{issueKey}] Duplicate — redirecting to parent {parent_key}")
            return {
                "type":              "duplicate",
                "message":           f"This is a duplicate ticket. See runbook for parent: {parent_key}",
                "parent_ticket_key": parent_key,
            }

        # ─────────────────────────────
        # CACHE HIT
        # ─────────────────────────────
        if ticket.get("checklist_steps") is not None and ticket.get("commands") is not None:
            print(f"📦 [{issueKey}] CACHE HIT")

            slack_result = await send_to_slack({
                "id": issueKey,
                "summary": ticket.get("summary"),
                "priority": ticket.get("priority"),
                "match_type": ticket.get("match_type"),
                "runbook_category": ticket.get("runbook_category"),
            })

            return {
                "checklist":                ticket["checklist_steps"],
                "commands":                 ticket["commands"],
                "runbook_title":            ticket.get("runbook_title"),

                # ✅ FIX: fallback to slack team if missing
                "runbook_category":         ticket.get("runbook_category") or (slack_result.get("team") if slack_result else None),

                "runbook_escalation_team":  ticket.get("runbook_escalation_team"),
                "match_type":               ticket.get("match_type"),

                "slack_channel":            slack_result.get("channel") if slack_result else None,
                "team":                     slack_result.get("team") if slack_result else None,

                "message":                  "Loaded from cache",
            }

        # ─────────────────────────────
        # CACHE MISS → RUN AGENT
        # ─────────────────────────────
        print(f"🤖 [{issueKey}] CACHE MISS — calling LLM...")

        state = {
            "id":      issueKey,
            "summary": ticket.get("summary", ""),
            "data":    ticket,
            "type":    None,
            "message": "",
        }

        result = await handle_runbook_flow(state)

        if result.get("type") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        checklist_steps: list = result.get("checklist_steps", [])
        raw_commands:    list = result.get("commands", [])

        commands = [
            {"label": f"Command {i + 1}", "command": cmd}
            for i, cmd in enumerate(raw_commands)
        ]

        # ─────────────────────────────
        # SLACK ROUTING
        # ─────────────────────────────
        slack_result = await send_to_slack({
            "id": issueKey,
            "summary": ticket.get("summary"),
            "priority": ticket.get("priority"),
            "match_type": result.get("match_type"),
            "runbook_category": result.get("runbook_category"),
        })

        # ✅ FIX: ensure category is never None
        final_category = result.get("runbook_category") or (slack_result.get("team") if slack_result else None)

        # ── cache in DB ──
        await update_ticket_runbook(
            issueKey,
            checklist_steps,
            commands,
            runbook_title           = result.get("runbook_title"),
            runbook_category        = final_category,  # ✅ FIX
            runbook_escalation_team = result.get("runbook_escalation_team"),
            match_type              = result.get("match_type"),
        )

        print(f"💾 [{issueKey}] Runbook cached in Supabase")

        return {
            "checklist":                checklist_steps,
            "commands":                 commands,
            "runbook_title":            result.get("runbook_title"),

            # ✅ FIX: always return category
            "runbook_category":         final_category,

            "runbook_escalation_team":  result.get("runbook_escalation_team"),
            "match_type":               result.get("match_type"),

            # ✅ always valid
            "slack_channel":            slack_result.get("channel") if slack_result else None,
            "team":                     slack_result.get("team") if slack_result else None,

            "message":                  result.get("message"),
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ get_runbook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ───────────── CREATE RUNBOOK ─────────────
@router.post("/runbooks")
async def create_runbook(data: dict):
    try:
        title           = (data.get("title")            or "").strip()
        category        = (data.get("category")         or "").strip()
        severity        = (data.get("severity")         or "").strip()
        steps           = (data.get("resolution_steps") or "").strip()
        escalation_team = (data.get("escalation_team")  or "").strip()

        if not title or not category or not severity or not steps or not escalation_team:
            return {
                "type":    "error",
                "message": "title, category, severity, escalation_team, and resolution_steps are required"
            }

        # ✅ same format as backfill script
        embed_text = f"""
    Title: {title}
    Category: {category}
    Symptoms: {data.get('symptoms', '')}
    Keywords: {data.get('keywords', title)}
    Resolution: {steps}
    """

        embedding = await get_embedding(embed_text)
        if embedding:
            embedding = [float(x) for x in embedding]

        payload = {
            "title":                    title,
            "category":                 category,
            "severity":                 severity,
            "keywords":                 data.get("keywords")                  or title,
            "symptoms":                 data.get("symptoms")                  or "",
            "resolution_steps":         steps,
            "escalation_team":          escalation_team,
            "owner":                    data.get("owner")                     or None,
            "estimated_resolution_time":data.get("estimated_resolution_time") or None,
            "ci_asset":                 data.get("ci_asset")                  or None,
            "status":                   "Active",
            "embedding":                embedding,
        }

        saved = await insert_runbook(payload)

        if not saved:
            return {"type": "error", "message": "Failed to save runbook to database"}

        print(f"✅ New runbook created: {title} (id={saved.get('id')})")

        return {
            "type":    "success",
            "message": "Runbook created successfully",
            "id":      saved.get("id"),
        }

    except Exception as e:
        print(f"❌ create_runbook error: {e}")
        return {"type": "error", "message": str(e)}
    

# ───────────── ESCALATE TICKET ─────────────
@router.post("/tickets/{issueKey}/escalate")
async def escalate_ticket(issueKey: str):
    try:
        tickets = await get_all_tickets()
        ticket = next((t for t in tickets if t["issue_key"] == issueKey), None)

        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {issueKey} not found")

        state = {
            "id": issueKey,
            "summary": ticket.get("summary"),
            "priority": ticket.get("priority"),
            "match_type": ticket.get("match_type"),
            "runbook_category": ticket.get("runbook_category"),
        }

        result = await send_to_slack(state)

        if not result or not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Slack routing failed: {result.get('error') if result else 'Unknown error'}"
            )

        # ✅ FIX: ensure category is always available
        final_category = ticket.get("runbook_category") or result.get("team")

        # ✅ OPTIONAL BUT IMPORTANT: persist AI category
        if not ticket.get("runbook_category") and final_category:
            await update_ticket_runbook(
                issueKey,
                ticket.get("checklist_steps"),
                ticket.get("commands"),
                runbook_title           = ticket.get("runbook_title"),
                runbook_category        = final_category,  # ✅ store AI category
                runbook_escalation_team = ticket.get("runbook_escalation_team"),
                match_type              = ticket.get("match_type"),
            )

        return {
            "type": "success",
            "message": "Ticket escalated successfully",

            # ✅ consistent output
            "team": final_category,
            "channel": result.get("channel"),
            "match_type": result.get("match_type"),
        }

    except Exception as e:
        print(f"❌ escalate_ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))   


