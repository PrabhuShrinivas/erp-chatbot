import pytest
from app.safety.numeric_guard import NumericConsistencyGuard
from app.metrics.base import ComputedFact

def test_numeric_guard_accepts_valid():
    guard = NumericConsistencyGuard()
    
    facts = [
        ComputedFact(
            fact_id="123",
            metric="outstanding",
            metric_version="v1",
            value=15000.50,
            unit="amount",
            currency="INR",
            provenance={}
        )
    ]
    
    # Valid output
    answer = "The outstanding amount is ₹15,000.50."
    assert guard.verify(answer, facts) is True
    
    # Valid output with alternative formatting
    answer2 = "The outstanding amount is 15000.5."
    assert guard.verify(answer2, facts) is True

def test_numeric_guard_rejects_hallucination():
    guard = NumericConsistencyGuard()
    
    facts = [
        ComputedFact(
            fact_id="123",
            metric="outstanding",
            metric_version="v1",
            value=15000.50,
            unit="amount",
            currency="INR",
            provenance={}
        )
    ]
    
    # Hallucinated number
    answer = "The outstanding amount is ₹20,000."
    assert guard.verify(answer, facts) is False
    
def test_numeric_guard_ignores_small_numbers():
    guard = NumericConsistencyGuard()
    
    facts = [
        ComputedFact(
            fact_id="123",
            metric="outstanding",
            metric_version="v1",
            value=15000.0,
            unit="amount",
            currency="INR",
            provenance={}
        )
    ]
    
    # 2 is a small number, probably part of English ("2 orders")
    answer = "The outstanding amount across 2 orders is ₹15,000."
    assert guard.verify(answer, facts) is True
