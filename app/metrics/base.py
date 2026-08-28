from typing import Any, Protocol
from datetime import date
from pydantic import BaseModel
import uuid

class ComputedFact(BaseModel):
    fact_id: str
    metric: str
    metric_version: str
    value: Any
    unit: str
    currency: str | None = None
    entity_id: uuid.UUID | None = None
    as_of_date: date | None = None
    provenance: dict[str, Any]

class MetricExecutor(Protocol):
    async def execute(self, session, **kwargs) -> ComputedFact:
        ...
