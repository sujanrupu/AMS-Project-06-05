import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_DOMAIN    = os.getenv("JIRA_DOMAIN")
    SERVICE_DESK_ID = os.getenv("SERVICE_DESK_ID")
    REQUEST_TYPE_ID = os.getenv("REQUEST_TYPE_ID")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")