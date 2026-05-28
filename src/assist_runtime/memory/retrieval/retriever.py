from typing import List
from assist_runtime.memory.embedders.base import BaseEmbedder
from assist_runtime.memory.vector_store.base import BaseVectorStore
from assist_runtime.memory.schemas.retrieved_chunk import RetrievedChunk

class Retriever:
    """Embeds a query and searches the vector store. No LLM calls."""
    # it doesn't care which specific technology you use. You can pass it an OpenAI embedder
    # and a Pinecone database today, or swap them out for a Cohere embedder and a Chroma 
    # database tomorrow
    def __init__(self, embedder: BaseEmbedder, vector_store: BaseVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    # What the embedder object looks like inside Python's memory:
    # embedder_object = {
    #     "model_name": "text-embedding-3-small",  # Data
    #     "api_key": "sk-12345...",                 # Data
    #     "embed": <function embed at 0x7f81a>       # The actual function!
    # }
    # In Python, the retriever does not care if the embedder_object uses OpenAI or Cohere.
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """Retrieve chunks from the vector store based on semantic similarity."""
        query_embedding = self.embedder.embed(query)
        return self.vector_store.search(query_embedding, top_k=top_k)
