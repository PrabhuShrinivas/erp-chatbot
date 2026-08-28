from pydantic import BaseModel, Field
from typing import Literal

class QueryPlan(BaseModel):
    operation: Literal["metric", "comparison", "trend"] = Field(description="The type of operation to perform.")
    metric: str = Field(description="The name of the metric to calculate, e.g., 'outstanding', 'on_time_delivery', 'stock_in_hand'.")
    metric_version: str = Field(description="The version of the metric, e.g., 'v1'.", default="v1")
    
    entity_name: str | None = Field(description="The name of the party or material mentioned in the query.", default=None)
    entity_type: Literal["customer", "supplier", "material"] | None = Field(description="The type of entity.", default=None)
    
    time_range: Literal["today", "yesterday", "current_month", "previous_month", "current_financial_year", "specific", "as_of"] | None = Field(description="The time scope.", default=None)
    specific_date: str | None = Field(description="A specific date if mentioned, in YYYY-MM-DD format.", default=None)
