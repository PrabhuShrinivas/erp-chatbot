from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import time
from app.db.session import get_db
from app.ingestion.normalize import QuestionNormalizer
from app.nlq.planner import LLMPlanner
from app.nlq.entity_resolution import EntityResolver
from app.safety.answerability import AnswerabilityEngine
from app.metrics.registry import registry
from app.rendering.renderer import AnswerRenderer
from app.safety.numeric_guard import NumericConsistencyGuard
from app.core.logging import setup_logging

logger = setup_logging()
router = APIRouter()

normalizer = QuestionNormalizer()
planner = LLMPlanner()
resolver = EntityResolver()
answerability_engine = AnswerabilityEngine()
renderer = AnswerRenderer()
numeric_guard = NumericConsistencyGuard()

class AskRequest(BaseModel):
    question: str

class FactResponse(BaseModel):
    fact_id: str
    metric: str
    value: float
    unit: str
    provenance: dict

class AskResponse(BaseModel):
    status: str
    request_id: str
    answer: str
    reason: str | None = None
    facts: list[FactResponse] | None = None

@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, session: AsyncSession = Depends(get_db)):
    req_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 1. Normalize
    norm_q = normalizer.normalize(request.question)
    
    try:
        # 2. Plan
        plan = await planner.generate_plan(norm_q)
        
        # 3. Resolve Entity
        resolved_entity_id = None
        if plan.entity_name:
            if plan.entity_type in ("customer", "supplier", "both"):
                resolved_entity_id = await resolver.resolve_party(session, plan.entity_name)
            elif plan.entity_type == "material":
                resolved_entity_id = await resolver.resolve_material(session, plan.entity_name)
                
        # 4. Answerability
        decision = answerability_engine.evaluate(plan, str(resolved_entity_id) if resolved_entity_id else None)
        
        if not decision.is_answerable:
            logger.info(f"Request {req_id} abstained: {decision.reason}")
            return AskResponse(
                status="abstained",
                request_id=req_id,
                answer="I cannot answer this question deterministically.",
                reason=decision.reason
            )
            
        # 5. Execute Metric
        executor = registry.get(plan.metric, plan.metric_version)
        if not executor:
            raise ValueError("Metric disappeared from registry after answerability check")
            
        # Pass required kwargs depending on metric
        kwargs = {}
        if plan.entity_type in ("customer", "supplier") and resolved_entity_id:
            kwargs["party_id"] = resolved_entity_id
        if plan.entity_type == "material" and resolved_entity_id:
            kwargs["material_code"] = resolved_entity_id
            
        fact = await executor.execute(session, **kwargs)
        facts = [fact]
        
        # 6. Render Answer
        final_answer = renderer.render(facts)
        
        # 7. Numeric Guard
        if not numeric_guard.verify(final_answer, facts):
            logger.error(f"Numeric Guard rejected response for {req_id}")
            return AskResponse(
                status="abstained",
                request_id=req_id,
                answer="Safety guard prevented returning this answer due to numerical inconsistency.",
                reason="Numeric Consistency Guard Failed"
            )
            
        logger.info(f"Request {req_id} completed successfully in {time.time() - start_time:.2f}s")
        
        return AskResponse(
            status="answered",
            request_id=req_id,
            answer=final_answer,
            facts=[
                FactResponse(
                    fact_id=f.fact_id,
                    metric=f.metric,
                    value=float(f.value),
                    unit=f.unit,
                    provenance=f.provenance
                ) for f in facts
            ]
        )
        
    except Exception as e:
        logger.exception(f"Error processing request {req_id}: {e}")
        return AskResponse(
            status="error",
            request_id=req_id,
            answer="An internal error occurred while processing your request.",
            reason=str(e)
        )
