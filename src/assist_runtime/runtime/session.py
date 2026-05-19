#this represents a live runtime conversation or session

from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime
from assist_runtime.runtime.context import ExecutionContext


@dataclass
class Session:

    """
    Active conversation session
    """

    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    
    created_at: datetime = field(
        default_factory=datetime.utcnow
    )
    
    updated_at: datetime = field(
        default_factory=datetime.utcnow
    )
    
    context: ExecutionContext = field(
        default_factory=ExecutionContext
    )

    message_history: list[dict] = field(
        default_factory=list
    )

    active_tools: list[str] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    def add_message(
        self,
        role: str,
        content: str
    ) -> None:

        """
        Add a message to the history
        """

        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })

        self.updated_at = datetime.utcnow()
        
    # def to_dict(self) -> dict:
    #     """
    #     Convert session to dictionary
    #     """
    #     return {
    #         "session_id": self.session_id,
    #         "created_at": self.created_at,
    #         "updated_at": self.updated_at,
    #         "context": self.context.to_dict(),
    #         "message_history": self.message_history,
    #         "active_tools": self.active_tools,
    #         "metadata": self.metadata
    #     }
        
    #missing def persist_session(self) -> None:
        #save session to disk or db    
        
    #missing def load_session(self) -> None:
        #load session from disk or db