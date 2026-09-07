from pydantic import BaseModel, Field
from typing import Literal

class MetricStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step, e.g., 'step_1'")
    type: Literal["metric"] = "metric"
    metric: str = Field(description="The name of the metric to calculate, e.g., 'outstanding', 'on_time_delivery', 'stock_in_hand'.")
    metric_version: str = Field(description="The version of the metric, e.g., 'v1'.", default="v1")
    entity_name: str | None = Field(description="The name of the party or material mentioned in the query.", default=None)
    entity_type: Literal["party", "material"] | None = Field(description="The type of entity.", default=None)
    date_from: str | None = Field(description="Start date (inclusive) in YYYY-MM-DD format. Null means no lower bound.", default=None)
    date_to: str | None = Field(description="End date (inclusive) in YYYY-MM-DD format. Null means no upper bound (i.e. today).", default=None)
    group_by: Literal["party", "material", "time", "all"] | None = Field(description="Dimension to group by. Use 'all' for aggregate totals across all entities.", default=None)

class CompareStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step")
    type: Literal["compare"] = "compare"
    operation: Literal["greater_than", "less_than", "percentage_change", "difference"] = Field(description="The comparison operation")
    input_steps: list[str] = Field(description="List of step_ids to compare")

class FilterStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step")
    type: Literal["filter"] = "filter"
    input_step: str = Field(description="The step_id of the list to filter")
    condition: str = Field(description="The logical condition to apply")

class AppendStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step, e.g., 'step_3'")
    type: Literal["append"] = "append"
    input_steps: list[str] = Field(
        description="List of step_ids whose results will be concatenated into a single flat list. "
                    "Use this when the user asks for the same (or related) metric across multiple distinct entities."
    )

class SortStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step")
    type: Literal["sort"] = "sort"
    input_step: str = Field(description="The step_id of the list to sort")
    order: Literal["asc", "desc"] = Field(description="Sort order: 'asc' for ascending, 'desc' for descending")

class LimitStep(BaseModel):
    step_id: str = Field(description="Unique ID for this step")
    type: Literal["limit"] = "limit"
    input_step: str = Field(description="The step_id of the list to limit")
    limit: int = Field(description="Number of items to keep")

class QueryPlan(BaseModel):
    steps: list[MetricStep | CompareStep | FilterStep | AppendStep | SortStep | LimitStep] = Field(description="List of execution steps")
    final_output_step: str = Field(description="The step_id that produces the final answer")
