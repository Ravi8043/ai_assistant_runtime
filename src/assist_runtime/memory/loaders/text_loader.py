from sqlalchemy import ReleaseSavepointClause
from langchain_community.document_loaders import TextLoader
from assist_runtime.memory.loaders.base import BaseLoader
from assist_runtime.memory.schemas.document import RawDocument

from typing import List 

class TextLoader(BaseLoader):
    

    def load(self, path: str) -> List[RawDocument]:
        loader = TextLoader(path)
        docs = loader.load()
        return [
            RawDocument(
                content=doc.page_content,
                metadata=doc.metadata,
            ) for doc in docs
        ]