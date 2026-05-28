from __future__ import annotations
from typing import List
from assist_runtime.memory.schemas.retrieved_chunk import RetrievedChunk

class WorkflowContextBuilder:
    """Assembles focused context for LLM calls within workflows."""
    
    # It is a bridge between your workflow code and the raw retrieved chunks.
    # Its job is simple: take a list of chunks and format them nicely so the LLM
    # can actually understand the structure.
    # This class takes those pieces, groups them by where they came from, formats them with 
    # clean Markdown headers (# and ##), and ensures the final text isn't too long for the 
    # LLM's memory window.

    def __init__(self, max_context_chars: int = 12000):
        # max_context_chars: Controls how many characters of context you send to the LLM.
        
        self.max_context_chars = max_context_chars
        self._sections: List[tuple[str, str]] = []

    def add_section(
        self, 
        header: str, 
        content: str
    ) -> WorkflowContextBuilder:

        # add_section: Lets you inject extra bits of text (like instructions, rules, or 
        # short notes) directly into the context under a custom header.
        #lets you add non database info to the context.
        
        self._sections.append((header, content))

        #returning self is for method chaining
        #so we can do builder.add_section(...).add_section(...).build()
        return self

    def add_retrieved_chunks(
        self,
        chunks: List[RetrievedChunk],
        header: str = "Retrieved Context",
    ) -> WorkflowContextBuilder:
    
        """
        # add_retrieved_chunks: This is the main method that processes the chunks coming 
        # from your retriever. It groups all chunks that belong to the same file (based on 
        # metadata["source"]), formats each file's content under a "## source" header,
        # and joins them together.
        """
        
        """
        grouped = {
            "onboarding.md": ["Welcome to the team.", "Office hours are 9-5."],
            "benefits.pdf": ["Health insurance is covered."]
        }

        ->

        # Retrieved Context

        ## onboarding.md
        Welcome to the team.
        Office hours are 9-5.

        ## benefits.pdf
        Health insurance is covered.
        """
        
        grouped: dict[str, List[str]] = {}
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            grouped.setdefault(source, []).append(chunk.text)

        lines = [f"# {header}\n"]
        for source, texts in grouped.items():
            lines.append(f"## {source}\n")
            lines.extend(texts)
            lines.append("")
        self._sections.append((header, "\n".join(lines)))
        return self

    def build(self) -> str:

        # build: This final method glues all the added sections together into one big string,
        # adds a main title (#), and chops it off if it exceeds your defined max_context_chars.
        # This is the string you actually paste into your LLM prompt.
        """Assemble all sections, truncate to limit."""
        
        full = "\n\n".join(
            f"# {h}\n{c}" for h, c in self._sections
        )
        if len(full) > self.max_context_chars:
            full = full[:self.max_context_chars] + "\n\n[context truncated]"
        return full
