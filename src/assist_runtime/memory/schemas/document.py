from pydantic import BaseModel

from typing import Any, Dict

class RawDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]

