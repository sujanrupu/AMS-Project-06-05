"""
modules/runbook_execution/prompt.py

All LLM prompts for the Guided Runbook Execution module.
Keeping prompts here makes them easy to update without
touching business logic in agent.py.
"""


# ─────────────────────────────────────────────────────────────
# PROMPT 1 — Runbook-grounded checklist + commands
# Used when a matching runbook IS found in Supabase.
# ─────────────────────────────────────────────────────────────
RUNBOOK_CHECKLIST_PROMPT = """You are a senior IT Site Reliability Engineer.

An incident ticket has been received:
  Summary     : {summary}
  Description : {description}

The most relevant runbook for this incident is:
  Title      : {runbook_title}
  Category   : {runbook_category}
  Severity   : {runbook_severity}
  Symptoms   : {runbook_symptoms}

Reference resolution steps from the runbook:
{runbook_steps}

Your task — produce TWO things:

1. CHECKLIST
   A personalised, ordered checklist for THIS specific incident.
   Replace generic placeholders with concrete values from the ticket.
   Maximum 8 steps. Each step on its own line, prefixed with "STEP: ".

2. COMMANDS
   The exact shell / CLI commands an engineer should run.
   Maximum 6 commands. Each command on its own line, prefixed with "CMD: ".
   Only include safe, read-only or restart commands — never destructive ones.
   If no commands apply, write "CMD: N/A".

Output format (no extra text, no markdown headers):
STEP: <step text>
STEP: <step text>
...
CMD: <command>
CMD: <command>
...
"""


# ─────────────────────────────────────────────────────────────
# PROMPT 2 — AI-only fallback (no runbook match)
# Used when no runbook is found in Supabase.
# ─────────────────────────────────────────────────────────────
FALLBACK_CHECKLIST_PROMPT = """You are a senior IT Site Reliability Engineer.

An incident ticket has been received with NO matching runbook:
  Summary     : {summary}
  Description : {description}

Generate a generic but practical troubleshooting checklist for this incident.

Your task — produce TWO things:

1. CHECKLIST
   Maximum 6 steps. Each step on its own line, prefixed with "STEP: ".

2. COMMANDS
   Maximum 4 safe diagnostic commands. Each on its own line, prefixed with "CMD: ".
   If none apply, write "CMD: N/A".

Output format (no extra text, no markdown headers):
STEP: <step text>
STEP: <step text>
...
CMD: <command>
CMD: <command>
...
"""