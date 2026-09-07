from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.nlq.schemas import QueryPlan, MetricStep, CompareStep, FilterStep, AppendStep, SortStep, LimitStep
from app.metrics.registry import registry
import operator

class DAGExecutor:
    async def execute(self, session: AsyncSession, plan: QueryPlan, resolved_entities: dict[str, Any]) -> dict[str, Any]:
        """
        Executes a QueryPlan DAG.
        Returns a dictionary mapping step_id to its result (e.g., a ComputedFact or list of ComputedFacts).
        """
        results = {}
        
        # Determine execution order (simplistic approach: they are already ordered topologically by LLM, or we resolve dependencies)
        # Assuming steps are in order of execution for now.
        for step in plan.steps:
            if isinstance(step, MetricStep):
                executor = registry.get(step.metric, step.metric_version)
                if not executor:
                    raise ValueError(f"Metric {step.metric} v{step.metric_version} not found in registry")
                
                kwargs = {}
                resolved_id = resolved_entities.get(step.step_id)
                if step.entity_type == "party" and resolved_id:
                    kwargs["party_id"] = resolved_id
                if step.entity_type == "material" and resolved_id:
                    kwargs["material_code"] = resolved_id
                
                if getattr(step, "group_by", None):
                    kwargs["group_by"] = step.group_by

                # Resolve date bounds from the LLM-computed fields
                from datetime import date as _date
                def _parse_date(s):
                    if s:
                        try:
                            return _date.fromisoformat(s)
                        except ValueError:
                            return None
                    return None

                date_from = _parse_date(getattr(step, "date_from", None))
                date_to = _parse_date(getattr(step, "date_to", None))

                if date_from:
                    kwargs["date_from"] = date_from
                if date_to:
                    kwargs["as_of_date"] = date_to   # existing param name in metrics

                # Metrics can return a single ComputedFact or a list of ComputedFacts
                fact = await executor.execute(session, **kwargs)
                results[step.step_id] = fact
                
            elif isinstance(step, CompareStep):
                from app.metrics.base import ComputedFact
                inputs = []
                for dep_id in step.input_steps:
                    dep_id_clean = dep_id.strip()
                    dep_result = results.get(dep_id_clean)
                    if not dep_result:
                        raise ValueError(f"Dependency {dep_id_clean} not found for compare step {step.step_id}")
                    inputs.append(dep_result)
                
                if len(inputs) < 2:
                    raise ValueError(f"Compare step {step.step_id} requires at least 2 inputs")
                    
                in1 = inputs[0]
                in2 = inputs[1]
                
                def _do_compare(v1, v2, op):
                    if op == "greater_than": return v1 > v2
                    elif op == "less_than": return v1 < v2
                    elif op == "percentage_change": return ((v1 - v2) / v2) * 100 if v2 != 0 else float('inf')
                    elif op == "difference": return v1 - v2
                    else: raise ValueError(f"Unknown comparison operation: {op}")

                def _get_unit(op, base_unit):
                    if op in ("greater_than", "less_than"): return "boolean"
                    if op == "percentage_change": return "percentage"
                    return base_unit

                if isinstance(in1, list) and isinstance(in2, list):
                    map1 = {f.entity_id: f for f in in1 if f.entity_id}
                    map2 = {f.entity_id: f for f in in2 if f.entity_id}
                    
                    common_entities = set(map1.keys()).intersection(set(map2.keys()))
                    res_list = []
                    for eid in common_entities:
                        f1 = map1[eid]
                        f2 = map2[eid]
                        res_val = _do_compare(f1.value, f2.value, step.operation)
                        res_list.append(ComputedFact(
                            fact_id=f"cmp_{step.step_id}_{eid}",
                            metric=f"compare_{step.operation}",
                            metric_version="v1",
                            value=res_val,
                            unit=_get_unit(step.operation, f1.unit),
                            entity_id=eid,
                            provenance={"inputs": [f1.fact_id, f2.fact_id]}
                        ))
                    results[step.step_id] = res_list
                else:
                    if isinstance(in1, list): in1 = in1[0]
                    if isinstance(in2, list): in2 = in2[0]

                    def _fact_provenance_summary(f):
                        """Extract display metadata from a fact for compare provenance."""
                        prov = f.provenance or {}
                        return {
                            "entity_name": f.entity_name,
                            "metric": f.metric,
                            "value": float(f.value),
                            "date_from": prov.get("date_from"),
                            "date_to": prov.get("date_to"),
                            "fact_id": f.fact_id,
                        }

                    res_val = _do_compare(in1.value, in2.value, step.operation)
                    results[step.step_id] = ComputedFact(
                        fact_id=f"cmp_{step.step_id}",
                        metric=f"compare_{step.operation}",
                        metric_version="v1",
                        value=res_val,
                        unit=_get_unit(step.operation, in1.unit),
                        provenance={
                            "operation": step.operation,
                            "input1": _fact_provenance_summary(in1),
                            "input2": _fact_provenance_summary(in2),
                            # legacy field kept for backward compat
                            "inputs": [in1.fact_id, in2.fact_id],
                        }
                    )
            
            elif isinstance(step, FilterStep):
                input_result = results.get(step.input_step)
                if not input_result:
                    raise ValueError(f"Dependency {step.input_step} not found for filter step {step.step_id}")

                if not isinstance(input_result, list):
                    input_result = [input_result]

                import re as _re
                filtered = []
                condition = step.condition.strip()

                # ── Pattern 1: party in ('name1', 'name2', ...)  ──────────────────
                # Matches entity_name against a set of names (case-insensitive, partial match).
                party_in_match = _re.match(
                    r"^party\s+in\s*\(([^)]+)\)$", condition, _re.IGNORECASE
                )
                if party_in_match:
                    raw_names = party_in_match.group(1)
                    # Extract quoted or unquoted tokens separated by commas
                    target_names = [
                        t.strip().strip("'\"").lower()
                        for t in raw_names.split(",")
                        if t.strip().strip("'\"")
                    ]
                    for item in input_result:
                        item_name = (item.entity_name or "").lower()
                        # Substring match so "shrinivas" matches "Shrinivas Prabhu" etc.
                        if any(target in item_name or item_name in target for target in target_names):
                            filtered.append(item)
                    results[step.step_id] = filtered
                    continue

                # ── Pattern 2: numeric comparison  >/</<=/>=/<op> <number>  ────────
                numeric_match = _re.match(r"^(>=|<=|==|!=|>|<)\s*([\d.]+)$", condition)
                if numeric_match:
                    import operator as _op
                    ops = {
                        ">": _op.gt, "<": _op.lt, "==": _op.eq,
                        "!=": _op.ne, ">=": _op.ge, "<=": _op.le,
                    }
                    op_str = numeric_match.group(1)
                    val = float(numeric_match.group(2))
                    op_func = ops[op_str]
                    for item in input_result:
                        if op_func(item.value, val):
                            filtered.append(item)
                    results[step.step_id] = filtered
                    continue

                # ── Unknown condition format — raise clearly instead of silently passing all ──
                raise ValueError(
                    f"FilterStep '{step.step_id}' has an unsupported condition format: '{condition}'. "
                    "Supported formats: 'party in (\"name1\", \"name2\")' or '<op> <number>' (e.g. '> 1000')."
                )

            elif isinstance(step, AppendStep):
                # Concatenate results from multiple prior steps into a single flat list.
                combined = []
                for dep_id in step.input_steps:
                    dep_id_clean = dep_id.strip()
                    dep_result = results.get(dep_id_clean)
                    if dep_result is None:
                        raise ValueError(
                            f"Dependency '{dep_id_clean}' not found for append step '{step.step_id}'. "
                            f"Make sure input steps are ordered before the append step."
                        )
                    if isinstance(dep_result, list):
                        combined.extend(dep_result)
                    else:
                        combined.append(dep_result)
                results[step.step_id] = combined

            elif isinstance(step, SortStep):
                input_result = results.get(step.input_step)
                if not input_result:
                    raise ValueError(f"Dependency {step.input_step} not found for sort step {step.step_id}")
                
                if not isinstance(input_result, list):
                    input_result = [input_result]
                
                reverse = step.order == "desc"
                # Sort based on the 'value' field of ComputedFact
                sorted_result = sorted(input_result, key=lambda x: x.value, reverse=reverse)
                results[step.step_id] = sorted_result

            elif isinstance(step, LimitStep):
                input_result = results.get(step.input_step)
                if not input_result:
                    raise ValueError(f"Dependency {step.input_step} not found for limit step {step.step_id}")
                
                if not isinstance(input_result, list):
                    input_result = [input_result]
                
                results[step.step_id] = input_result[:step.limit]

        return results
