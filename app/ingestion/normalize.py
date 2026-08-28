class QuestionNormalizer:
    def normalize(self, question: str) -> str:
        """
        Cleans up filler words and normalizes Hinglish intent.
        For Phase 1, we do basic string cleaning. 
        In production, this could optionally be a fast local LLM pass.
        """
        q = question.lower().strip()
        
        # Remove common filler words
        fillers = ["arre", "haan", "woh", "bhai", "yaar", "please", "batao"]
        
        for f in fillers:
            # simple regex to replace filler words
            import re
            q = re.sub(rf'\b{f}\b', '', q)
            
        q = q.replace("?", "").strip()
        # Reduce multiple spaces
        q = " ".join(q.split())
        
        return q
