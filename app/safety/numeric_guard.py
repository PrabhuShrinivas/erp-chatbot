import re
from app.metrics.base import ComputedFact

class NumericConsistencyGuard:
    # Matches ISO dates like 2026-08-31 — strip these before numeric extraction
    _DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')
    # Matches UUIDs — strip so their digit segments don't trigger false guard failures
    _UUID_PATTERN = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)

    def verify(self, final_answer: str, facts: list[ComputedFact]) -> bool:
        """
        Parses the final text answer and extracts all numbers.
        Ensures that any significant factual number (like an amount or percentage)
        was actually present in the provided ComputedFacts.
        """
        # Remove UUIDs first (entity_id fallback labels), then ISO date strings
        sanitized = self._UUID_PATTERN.sub('', final_answer)
        sanitized = self._DATE_PATTERN.sub('', sanitized)

        # Extract all numbers from the sanitized text, including negative numbers and currencies
        raw_numbers = re.findall(r'-?\d+(?:,\d+)*(?:\.\d+)?', sanitized)

        # Convert found string numbers to float for comparison
        found_values = []
        for num_str in raw_numbers:
            clean_str = num_str.replace(',', '')
            try:
                found_values.append(float(clean_str))
            except ValueError:
                pass

        trusted_values = []
        for fact in facts:
            try:
                trusted_values.append(float(fact.value))
            except (ValueError, TypeError):
                pass

        # Recursively collect all numeric values from provenance at any nesting depth.
        # This covers flat keys (total_invoices, total_payments), compare input dicts
        # (input1.value, input2.value), and any future nested structures.
        def _collect_provenance_numbers(obj, out: list):
            if isinstance(obj, dict):
                for v in obj.values():
                    _collect_provenance_numbers(v, out)
            elif isinstance(obj, list):
                for item in obj:
                    _collect_provenance_numbers(item, out)
            elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
                out.append(float(obj))

        for fact in facts:
            if fact.provenance:
                _collect_provenance_numbers(fact.provenance, trusted_values)


        for val in found_values:
            # Ignore small integers that might be part of grammar (e.g. "1 customer", "2 items")
            if val < 3000 and float(val).is_integer():
                continue

            # If a significant number is found, it MUST match a trusted value (within rounding tolerance)
            # We also check against abs(t_val) because renderer often uses absolute values for negative differences or percentage drops
            is_trusted = any(abs(val - t_val) < 0.5 or abs(val - abs(t_val)) < 0.5 for t_val in trusted_values)
            if not is_trusted:
                print(f"NumericGuard failed on value {val}. Trusted values: {trusted_values}")
                return False

        return True
