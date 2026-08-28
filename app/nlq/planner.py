import openai
import instructor
from app.core.config import settings
from app.nlq.schemas import QueryPlan

# Configure OpenAI client for OpenRouter
client = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.LLM_API_KEY,
)

# Patch with instructor to ensure structured output (handles retries and schema enforcement)
instructor_client = instructor.from_openai(client, mode=instructor.Mode.JSON)

class LLMPlanner:
    async def generate_plan(self, normalized_question: str) -> QueryPlan:
        system_prompt = """
        You are an AI assistant that translates natural language business questions into a structured QueryPlan.
        You MUST NEVER calculate numbers, generate SQL, or return a final factual answer.
        Your ONLY job is to identify the metric, the entities, and the time range involved.
        
        Available metrics:
        - outstanding
        - on_time_delivery
        - stock_in_hand
        
        All metrics should default to version 'v1'.
        """
        
        plan = await instructor_client.chat.completions.create(
            model=settings.LLM_MODEL,
            response_model=QueryPlan,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": normalized_question}
            ],
            temperature=0.0
        )
        
        return plan
