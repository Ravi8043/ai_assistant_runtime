import json
import re


class StructuredOutputParser:

    def parse(self, text: str):

        """
        Extract JSON from model output safely.
        """

        try:
            return json.loads(text)

        except Exception:
            pass

        # fallback: extract json block
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return None

        return None