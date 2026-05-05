import httpx
import re
from core.config import Config
from repositories.ticket_repository import get_all_tickets

auth = (Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

BASE_URL = f"https://{Config.JIRA_DOMAIN}"


# ───────────── CREATE TICKET (ITSM - CORRECT) ─────────────
async def create_ticket(data, related=""):
    url = f"{BASE_URL}/rest/servicedeskapi/request"

    payload = {
        "serviceDeskId": Config.SERVICE_DESK_ID,
        "requestTypeId": Config.REQUEST_TYPE_ID,
        "requestFieldValues": {
            "summary": data.summary,
            "description": f"{data.description}\n\nRelated:\n{related}"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload, headers=headers, auth=auth)

        if res.status_code not in [200, 201]:
            print("❌ Jira create error:", res.text)
            return None

        return res.json()

    except Exception as e:
        print("❌ Exception in create_ticket:", str(e))
        return None


# ───────────── APPEND DUPLICATE (ITSM SAFE UPDATE) ─────────────
async def append_duplicate(parent_key, child_id, summary):
    url = f"{BASE_URL}/rest/api/3/issue/{parent_key}"

    new_text = f"[{child_id}] {summary}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=headers, auth=auth)

        if res.status_code != 200:
            print("❌ Failed to fetch parent issue:", res.text)
            return False

        issue = res.json()
        desc = issue.get("fields", {}).get("description")

        new_block = {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": new_text}
            ]
        }

        content = []

        if isinstance(desc, dict) and "content" in desc:
            content = desc["content"]

        content.append(new_block)

        payload = {
            "fields": {
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": content
                }
            }
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.put(url, json=payload, headers=headers, auth=auth)

        if res.status_code not in [200, 204]:
            print("❌ Error appending duplicate:", res.text)
            return False

        return True

    except Exception as e:
        print("❌ append_duplicate exception:", str(e))
        return False


# ───────────── CHILD ID GENERATION (FIXED + SAFE) ─────────────
async def generate_child_id(parent_key: str):
    tickets = await get_all_tickets()

    pattern = re.compile(rf"^{re.escape(parent_key)}\.(\d+)$")

    max_num = 0

    for t in tickets:
        issue_key = t.get("issue_key", "")

        # 🔥 SAFETY: ignore nested bad data like ABC-1.1.1
        if issue_key.count(".") > 1:
            continue

        match = pattern.match(issue_key)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

    return f"{parent_key}.{max_num + 1}"


# ───────────── DELETE ─────────────
async def delete_jira_ticket(issueKey: str):
    url = f"{BASE_URL}/rest/api/3/issue/{issueKey}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.delete(url, headers=headers, auth=auth)

        if res.status_code not in [200, 204]:
            print(f"❌ Jira delete failed {issueKey}:", res.text)
            return False

        return True

    except Exception as e:
        print("❌ delete_jira_ticket exception:", str(e))
        return False
    

# ───────────── UPDATE STATUS IN JIRA ─────────────
async def update_jira_status(issue_key: str):

    url = f"{BASE_URL}/rest/api/3/issue/{issue_key}/transitions"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=headers, auth=auth)

        if res.status_code != 200:
            print("❌ Failed to fetch transitions:", res.text)
            return False

        transitions = res.json().get("transitions", [])

        transition_id = None

        for t in transitions:
            name = t.get("name", "").lower()

            if any(k in name for k in ["done", "complete", "resolve", "close"]):
                transition_id = t.get("id")
                break

        if not transition_id:
            print("❌ No suitable transition found")
            return False

        payload = {
            "transition": {
                "id": transition_id
            }
        }

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json=payload, headers=headers, auth=auth)

        if res.status_code not in [200, 204]:
            print("❌ Jira status update failed:", res.text)
            return False

        return True

    except Exception as e:
        print("❌ update_jira_status exception:", str(e))
        return False