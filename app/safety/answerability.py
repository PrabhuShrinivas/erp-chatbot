from app.nlq.schemas import QueryPlan, MetricStep
from app.metrics.registry import registry
from pydantic import BaseModel

class AnswerabilityDecision(BaseModel):
    is_answerable: bool
    reason: str | None = None

class AnswerabilityEngine:
    def evaluate(self, plan: QueryPlan, resolved_entities: dict[str, str | None]) -> AnswerabilityDecision:
        for step in plan.steps:
            if isinstance(step, MetricStep):
                # 1. Check if metric is supported
                executor = registry.get(step.metric, step.metric_version)
                if not executor:
                    return AnswerabilityDecision(
                        is_answerable=False,
                        reason=f"Unsupported metric: {step.metric} version {step.metric_version}"
                    )
                    
                resolved_entity_id = resolved_entities.get(step.step_id)
                
                # 2. Check if entity was resolved when one was mentioned
                if step.entity_name and not resolved_entity_id:
                    return AnswerabilityDecision(
                        is_answerable=False,
                        reason=f"Could not resolve entity: {step.entity_name}"
                    )
                    
                # 3. Check specific metric constraints
                if step.metric == "outstanding" and not resolved_entity_id and step.group_by not in ("party", "all", "time"):
                    return AnswerabilityDecision(
                        is_answerable=False,
                        reason="Outstanding metric requires a specific customer entity, or group_by must be 'party', 'all', or 'time'."
                    )

                    
                if step.metric == "stock_in_hand" and not resolved_entity_id:
                    return AnswerabilityDecision(
                        is_answerable=False,
                        reason="Stock in hand requires a specific material."
                    )

        return AnswerabilityDecision(is_answerable=True)

