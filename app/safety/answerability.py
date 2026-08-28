from app.nlq.schemas import QueryPlan
from app.metrics.registry import registry
from pydantic import BaseModel

class AnswerabilityDecision(BaseModel):
    is_answerable: bool
    reason: str | None = None

class AnswerabilityEngine:
    def evaluate(self, plan: QueryPlan, resolved_entity_id: str | None) -> AnswerabilityDecision:
        # 1. Check if metric is supported
        executor = registry.get(plan.metric, plan.metric_version)
        if not executor:
            return AnswerabilityDecision(
                is_answerable=False,
                reason=f"Unsupported metric: {plan.metric} version {plan.metric_version}"
            )
            
        # 2. Check if entity was resolved when one was mentioned
        if plan.entity_name and not resolved_entity_id:
            return AnswerabilityDecision(
                is_answerable=False,
                reason=f"Could not resolve entity: {plan.entity_name}"
            )
            
        # 3. Check specific metric constraints
        if plan.metric == "outstanding" and not resolved_entity_id:
            return AnswerabilityDecision(
                is_answerable=False,
                reason="Outstanding metric requires a specific customer entity."
            )
            
        if plan.metric == "stock_in_hand" and not resolved_entity_id:
            return AnswerabilityDecision(
                is_answerable=False,
                reason="Stock in hand requires a specific material."
            )

        return AnswerabilityDecision(is_answerable=True)
