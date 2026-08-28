from app.metrics.base import ComputedFact

class AnswerRenderer:
    def render(self, facts: list[ComputedFact]) -> str:
        """
        Renders a natural language response deterministically based on facts.
        No LLM is used here to avoid hallucination of numbers.
        """
        if not facts:
            return "No data could be computed for your query."
            
        fact = facts[0]
        
        if fact.metric == "outstanding":
            return f"The outstanding amount is ₹{fact.value:,.2f}."
            
        elif fact.metric == "on_time_delivery":
            return f"The on-time delivery rate is {fact.value:.1f}%."
            
        elif fact.metric == "stock_in_hand":
            return f"The available stock in hand is {fact.value:.3f} units."
            
        return f"The computed value for {fact.metric} is {fact.value}."
