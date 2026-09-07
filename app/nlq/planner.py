import openai
import instructor
from datetime import date
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
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        system_prompt = f"""
        You are an AI assistant that translates natural language business questions into a structured QueryPlan.
        You MUST NEVER calculate numbers, generate SQL, or return a final factual answer.
        Your ONLY job is to identify the metrics, the entities, and the time ranges involved, and organize them into execution steps.

        Today's date is: {today_str}

        Available metrics:
        - outstanding
        - on_time_delivery
        - stock_in_hand

        All metrics should default to version 'v1'.

        ## Date Resolution Rules
        You MUST resolve all time expressions into concrete date_from and date_to strings (YYYY-MM-DD).
        A month always runs from the 1st to the last day of that month (28/29/30/31 as appropriate).
        A financial year runs from 1st April to 31st March.
        Always use today's date ({today_str}) as the reference when computing relative periods.

        | Expression | date_from | date_to |
        |---|---|---|
        | "today" / "now" | {today_str} | {today_str} |
        | "as of today" / "current" (outstanding balance) | null | {today_str} |
        | "this month" | first day of current month | last day of current month |
        | "last month" / "previous month" | first day of previous month | last day of previous month |
        | "next month" | first day of next month | last day of next month |
        | "this week" | Monday of current week | Sunday of current week |
        | "last week" | Monday of previous week | Sunday of previous week |
        | "this year" (calendar) | {today.year}-01-01 | {today.year}-12-31 |
        | "last year" (calendar) | {today.year - 1}-01-01 | {today.year - 1}-12-31 |
        | "this financial year" | Apr 1 of current FY start | Mar 31 of current FY end |
        | "last financial year" | Apr 1 of previous FY | Mar 31 of previous FY end |
        | "since <date>" | <date> | null |
        | "before <date>" | null | <date> |
        | "between <d1> and <d2>" | <d1> | <d2> |
        | "in <month> <year>" | <year>-<month>-01 | last day of that month |
        | no time mentioned (for outstanding/balance) | null | {today_str} |
        | no time mentioned (for flow metrics like invoices raised) | null | null |

        For outstanding (a balance/stock metric), if NO time is specified, set date_to to today ({today_str}) and date_from to null.
        For flow metrics (invoices raised, payments received, deliveries), if NO time is specified, leave both null.

        ## Step Building Rules
        - If the question asks for something completely outside the available metrics (like employees, CEO salary, statistical standard deviation, profitability, predictions, etc.), do NOT try to guess or map it to an existing metric. Instead, set the metric name to 'unsupported' so the system knows to decline it.
        - Use MetricStep to fetch raw data.
        - If the question asks "Which customers" or "Which materials" or "List all" or wants a list of metrics for each customer individually (e.g. "List on-time delivery rate of all customers"), set group_by to 'party' or 'material'.
        - If the question specifically asks for a single total/aggregate number across ALL customers (e.g. "total outstanding", "overall delivery rate"), set group_by to 'all' and leave entity_name null.
        - If the question asks for month-over-month, trend, or time-series breakdown for a specific entity (e.g. "outstanding of Naaga month over month for last 3 months"), set group_by to 'time' and set date_from/date_to to span the full period. The system will automatically bucket into months.
        - If the question is about a specific named customer or material, set entity_name and entity_type, leave group_by null.
        - Use CompareStep to compare two MetricStep results (e.g. this month vs last month, or entity A vs entity B).
          Example: "Whose outstanding is more, Shrinivas or Naaga?" -> step_1 (outstanding, Shrinivas) + step_2 (outstanding, Naaga) -> step_3 (CompareStep: operation 'greater_than', inputs: [step_1, step_2]).
        - Use FilterStep to filter a list result by a condition. The condition MUST follow one of these exact formats:
            * Entity name filter: party in ('name1', 'name2')
              Use this when the user wants results only for specific named parties/customers.
              Names should be written exactly as the user mentioned them (do NOT look up IDs).
              Example: "outstanding of shrinivas and naaga" with group_by party → filter condition: party in ('shrinivas', 'naaga')
            * Numeric value filter: <op> <number> where op is one of >, <, >=, <=, ==, !=
              Use this when the user wants to threshold by value.
              Example: "customers with outstanding > 1 lakh" → filter condition: > 100000
              IMPORTANT: For percentage metrics (like on_time_delivery), use the percentage value (0-100) directly (e.g. "greater than 50%" -> > 50, NOT > 0.5).

        - Use AppendStep to combine results from multiple MetricSteps into a single list when the user asks for the SAME (or related) metric across MULTIPLE distinct named entities.
          Example: "outstanding of Reliance and Naaga" → step_1 (outstanding, Reliance) + step_2 (outstanding, Naaga) → step_3 (AppendStep: [step_1, step_2]).
          Example: "stock of Steel Rod and Iron Sheet" → step_1 (stock_in_hand, Steel Rod) + step_2 (stock_in_hand, Iron Sheet) → step_3 (AppendStep: [step_1, step_2]).
          IMPORTANT: Always place AppendStep AFTER all of its input MetricSteps in the steps list.
        - Use SortStep to sort a list result by the metric value. Set 'order' to 'asc' for ascending (lowest first/worst) or 'desc' for descending (highest first/best).
          Example: "Top 3 customers with highest outstanding" -> MetricStep (outstanding) -> SortStep (order: desc) -> LimitStep (limit: 3).
          Example: "Whose delivery rate is worst?" -> MetricStep (on_time_delivery) -> SortStep (order: asc) -> LimitStep (limit: 1).
        - Use LimitStep to limit an array result to the top N items. Set 'limit' to the number provided in the query.
          Example: "Top 5 customers with highest ontime delivery rate" -> limit: 5. "Top customer..." -> limit: 1.
        - Set 'final_output_step' to the step_id of the step that produces the final answer.
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
