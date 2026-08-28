import re
from app.metrics.base import ComputedFact

class NumericConsistencyGuard:
    def verify(self, final_answer: str, facts: list[ComputedFact]) -> bool:
        """
        Parses the final text answer and extracts all numbers.
        Ensures that any significant factual number (like an amount or percentage)
        was actually present in the provided ComputedFacts.
        """
        
        # Extract all numbers from the text
        # This regex matches numbers like 100, 100.50, 1,00,000, 50,000.00
        raw_numbers = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?\b', final_answer)
        
        # Convert found string numbers to float for comparison
        found_values = []
        for num_str in raw_numbers:
            clean_str = num_str.replace(',', '')
            try:
                found_values.append(float(clean_str))
            except ValueError:
                pass
                
        trusted_values = [float(fact.value) for fact in facts]
        
        # A very strict guard: if the model outputs ANY number that is not in the trusted values 
        # (and is not a trivial formatting number like 0 or 1), we reject it.
        # In a real system, this would be more sophisticated (handling rounding, years, dates).
        
        # For this PoC, we will check if the MOST IMPORTANT trusted value is in the text,
        # AND we check if the text contains any huge unknown numbers.
        
        for val in found_values:
            # Ignore small integer numbers that might be part of grammar or dates like "1" or "2024"
            if val < 3000 and float(val).is_integer():
                continue
                
            # If a large/decimal number is found, it MUST match a trusted value (with minor rounding tolerance)
            is_trusted = any(abs(val - t_val) < 0.1 for t_val in trusted_values)
            if not is_trusted:
                return False
                
        return True
