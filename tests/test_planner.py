import pytest
from app.nlq.planner import LLMPlanner
from app.nlq.schemas import QueryPlan
from unittest.mock import patch, MagicMock

# A simple mock test to ensure that the planner correctly uses the Pydantic schema
# We mock out the actual LLM call to instructor.
@pytest.mark.asyncio
async def test_planner_schema_enforcement():
    planner = LLMPlanner()
    
    mock_plan = QueryPlan(
        operation="metric",
        metric="outstanding",
        metric_version="v1",
        entity_name="Sharma",
        entity_type="customer"
    )
    
    with patch("app.nlq.planner.instructor_client.chat.completions.create") as mock_create:
        # Mocking the async response from instructor
        async def mock_response(*args, **kwargs):
            return mock_plan
            
        mock_create.side_effect = mock_response
        
        result = await planner.generate_plan("What is Sharma's outstanding balance?")
        
        assert result.metric == "outstanding"
        assert result.entity_name == "Sharma"
        assert not hasattr(result, "sql")
        assert not hasattr(result, "answer")
