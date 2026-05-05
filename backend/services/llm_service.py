from groq import Groq
from core.config import Config

client = Groq(api_key=Config.GROQ_API_KEY)

async def call_llm(prompt: str):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()