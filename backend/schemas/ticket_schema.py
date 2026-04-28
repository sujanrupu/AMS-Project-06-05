from pydantic import BaseModel

class TicketRequest(BaseModel):
    name: str
    email: str
    summary: str
    description: str = ""