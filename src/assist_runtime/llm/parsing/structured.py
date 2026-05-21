import json
import re

class StructuredOutputParser:
    def parse(self, text: str):
        """
        Extract JSON from model output safely.
        """
        # 1. Remove <think> blocks
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        
        # 2. Try to extract markdown JSON block
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except Exception:
                pass
                
        # 3. Fallback: try raw json.loads
        try:
            return json.loads(text)
        except Exception:
            pass
            
        # 4. Fallback: find the first { and last } and try parsing
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                return json.loads(text[start_idx:end_idx+1])
            except Exception:
                pass
                
        return None