from app.metrics.base import ComputedFact


def _format_fact_value(fact: ComputedFact) -> str:
    """Format a ComputedFact value with the appropriate unit/currency label."""
    if fact.metric == "outstanding":
        return f"₹{fact.value:,.2f}"
    elif fact.metric == "on_time_delivery":
        return f"{fact.value:.1f}%"
    elif fact.metric == "stock_in_hand":
        return f"{fact.value:.3f} units"
    else:
        return str(fact.value)


def _date_range_clause(fact: ComputedFact) -> str:
    """Return a human-readable date range suffix from provenance, e.g. ' from 2026-04-01 to 2026-04-30'."""
    if not fact.provenance:
        return ""
    date_from = fact.provenance.get("date_from")
    date_to = fact.provenance.get("date_to")
    if date_from and date_to:
        return f" from {date_from} to {date_to}"
    if date_from:
        return f" from {date_from}"
    if date_to:
        return f" as of {date_to}"
    return ""


def _metric_label(metric: str) -> str:
    """Return a human-readable metric label."""
    return {
        "outstanding": "Outstanding",
        "on_time_delivery": "On-time delivery",
        "stock_in_hand": "Stock in hand",
    }.get(metric, metric.replace("_", " ").title())


class AnswerRenderer:
    def render(self, facts: list[ComputedFact]) -> str:
        """
        Renders a natural language response deterministically based on facts.
        No LLM is used here to avoid hallucination of numbers.
        """
        if not facts:
            return "No data could be computed for your query."
            
        if len(facts) > 1:
            if facts[0].unit == "boolean":
                matched = [f for f in facts if f.value]
                if not matched:
                    return "No entities matched the criteria."
                names = [f.entity_name or str(f.entity_id) for f in matched]
                return f"Found {len(matched)} matching entities: {', '.join(names)}"

            # Detect time-series (month-over-month) results
            is_time_series = all(
                f.provenance and f.provenance.get("group_by") == "time"
                for f in facts
            )
            if is_time_series:
                party_label = None
                # Try to get the party name from provenance or entity_id
                if facts[0].entity_id:
                    party_label = f" for entity"  # fallback; entity_name IS the period label here
                period_name = facts[0].provenance.get("party_name") if facts[0].provenance else None
                header = "Month-over-month outstanding:"
                lines = [header]
                for f in facts:
                    period = f.provenance.get("period", f.entity_name or "?")
                    lines.append(f"  {period}: ₹{f.value:,.2f}"
                                 f"  (invoices ₹{f.provenance.get('total_invoices', 0):,.2f},"
                                 f" payments ₹{f.provenance.get('total_payments', 0):,.2f})")
                return "\n".join(lines)

            # Check if this is an appended result containing multiple distinct metrics
            metrics_present = {f.metric for f in facts}
            if len(metrics_present) > 1:
                # Group by metric for clarity when multiple metric types are appended
                from collections import defaultdict
                grouped: dict[str, list] = defaultdict(list)
                for f in facts:
                    grouped[f.metric].append(f)

                sections = []
                for metric_name, metric_facts in grouped.items():
                    section_lines = [f"{metric_name.replace('_', ' ').title()}:"]
                    for f in metric_facts:
                        name = f.entity_name or str(f.entity_id)
                        section_lines.append(f"  {name}: {_format_fact_value(f)}")
                    sections.append("\n".join(section_lines))
                return "\n\n".join(sections)

            # Single-metric list (including appended same-metric results)
            # Use sentence format: "Outstanding for <name> <date_range> is <value>"
            lines = []
            for f in facts:
                name = f.entity_name or str(f.entity_id)
                date_clause = _date_range_clause(f)
                label = _metric_label(f.metric)
                lines.append(f"{label} for {name}{date_clause} is {_format_fact_value(f)}")
            return "\n".join(lines)
            
        fact = facts[0]

        # ── Compare results ───────────────────────────────────────────────────────
        if fact.metric.startswith("compare_"):
            prov = fact.provenance or {}
            in1 = prov.get("input1", {})
            in2 = prov.get("input2", {})
            operation = prov.get("operation", fact.metric.replace("compare_", ""))

            def _entity_clause(inp: dict) -> str:
                """Build 'Outstanding for Shrinivas from X to Y' from input summary."""
                label = _metric_label(inp.get("metric", ""))
                name = inp.get("entity_name") or ""
                date_from = inp.get("date_from")
                date_to = inp.get("date_to")
                date_str = ""
                if date_from and date_to:
                    date_str = f" from {date_from} to {date_to}"
                elif date_from:
                    date_str = f" from {date_from}"
                elif date_to:
                    date_str = f" as of {date_to}"
                if name:
                    return f"{label} for {name}{date_str}"
                return f"{label}{date_str}"

            def _value_clause(inp: dict) -> str:
                metric = inp.get("metric", "")
                val = inp.get("value", 0)
                if metric == "outstanding":
                    return f"₹{val:,.2f}"
                elif metric == "on_time_delivery":
                    return f"{val:.1f}%"
                elif metric == "stock_in_hand":
                    return f"{val:.3f} units"
                return str(val)

            e1 = _entity_clause(in1)
            e2 = _entity_clause(in2)

            if operation == "greater_than":
                # fact.value is True if in1 > in2, False if not
                if fact.value:
                    return f"{e1} ({_value_clause(in1)}) is greater than {e2} ({_value_clause(in2)})."
                else:
                    return f"{e2} ({_value_clause(in2)}) is greater than {e1} ({_value_clause(in1)})."

            elif operation == "less_than":
                if fact.value:
                    return f"{e1} ({_value_clause(in1)}) is less than {e2} ({_value_clause(in2)})."
                else:
                    return f"{e2} ({_value_clause(in2)}) is less than {e1} ({_value_clause(in1)})."

            elif operation == "difference":
                diff = abs(fact.value)
                higher_e, lower_e = (e1, e2) if in1.get("value", 0) >= in2.get("value", 0) else (e2, e1)
                metric_for_unit = in1.get("metric", "")
                if metric_for_unit == "outstanding":
                    diff_str = f"₹{diff:,.2f}"
                elif metric_for_unit == "on_time_delivery":
                    diff_str = f"{diff:.1f}%"
                else:
                    diff_str = str(diff)
                return f"{higher_e} is {diff_str} more than {lower_e}."

            elif operation == "percentage_change":
                direction = "increased" if fact.value >= 0 else "decreased"
                return f"{e1} has {direction} by {abs(fact.value):.1f}% compared to {e2}."

            # Fallback for unknown compare operations
            return f"{e1} vs {e2}: {fact.value}."

        # ── Single metric results ─────────────────────────────────────────────────
        if fact.metric == "outstanding":
            scope = fact.provenance.get("scope", None) if fact.provenance else None
            date_clause = _date_range_clause(fact)
            if scope == "all_customers":
                return f"Total outstanding{date_clause} across all customers is ₹{fact.value:,.2f}."
            elif fact.entity_name:
                return f"Outstanding for {fact.entity_name}{date_clause} is ₹{fact.value:,.2f}."
            return f"Outstanding{date_clause} is ₹{fact.value:,.2f}."

        elif fact.metric == "on_time_delivery":
            date_clause = _date_range_clause(fact)
            name = f" for {fact.entity_name}" if fact.entity_name else ""
            return f"On-time delivery rate{name}{date_clause} is {fact.value:.1f}%."


        elif fact.metric == "stock_in_hand":
            date_clause = _date_range_clause(fact)
            name = f" for {fact.entity_name}" if fact.entity_name else ""
            return f"Stock in hand{name}{date_clause} is {fact.value:.3f} units."

        return f"The computed value for {fact.metric} is {fact.value}."
