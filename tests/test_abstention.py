import pytest
from app.nlq.schemas import QueryPlan, MetricStep
from app.safety.answerability import AnswerabilityEngine
from app.metrics.registry import MetricRegistry

def test_answerability_unsupported_metric():
    engine = AnswerabilityEngine()
    
    plan = QueryPlan(
        steps=[MetricStep(step_id="step_1", metric="fake_metric", metric_version="v1")],
        final_output_step="step_1"
    )
    
    decision = engine.evaluate(plan, {})
    assert not decision.is_answerable
    assert "Unsupported metric" in decision.reason

def test_answerability_missing_entity():
    engine = AnswerabilityEngine()
    
    plan = QueryPlan(
        steps=[MetricStep(step_id="step_1", metric="outstanding", metric_version="v1", entity_name="Unknown Corp", entity_type="party")],
        final_output_step="step_1"
    )
    
    decision = engine.evaluate(plan, {})
    # The entity was not resolved (resolved_entities dict doesn't contain step_1 mapping)
    assert not decision.is_answerable
    assert "Could not resolve entity" in decision.reason

def test_answerability_outstanding_requires_entity():
    engine = AnswerabilityEngine()
    
    # User just asks "what is the outstanding" without an entity, and plan has no entity name
    plan = QueryPlan(
        steps=[MetricStep(step_id="step_1", metric="outstanding", metric_version="v1")],
        final_output_step="step_1"
    )
    
    decision = engine.evaluate(plan, {})
    assert not decision.is_answerable
    assert "Outstanding metric requires a specific customer entity" in decision.reason

