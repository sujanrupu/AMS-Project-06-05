import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .prompt import TEMPLATE

load_dotenv()

llm = ChatGroq(
    model_name=os.getenv("MODEL_NAME", "llama-3.1-8b-instant"),
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)

parser = JsonOutputParser()

prompt = PromptTemplate(
    input_variables=["description"],
    template=TEMPLATE
)

chain = prompt | llm | parser


# ─────────────────────────────────────────────
# LLM CLASSIFICATION ENGINE
# ─────────────────────────────────────────────
async def analyze_async(description: str):
    try:
        # validation
        if not isinstance(description, str) or len(description.strip()) < 5:
            raise ValueError("Invalid input")

        # ✅ ASYNC CALL (FIXED)
        result = await chain.ainvoke({"description": description})

        # safety check
        if not isinstance(result, dict):
            raise ValueError("Invalid LLM output format")

        return {
            "urgency": result.get("urgency", "Medium"),
            "impact": result.get("impact", "Medium"),
            "rationale": result.get("rationale", "No context available")
        }

    except Exception as e:
        print("❌ analyze_async error:", str(e))

        return {
            "urgency": "Medium",
            "impact": "Medium",
            "rationale": "Fallback triggered due to LLM/parsing failure; defaulting to Medium safely"
        }