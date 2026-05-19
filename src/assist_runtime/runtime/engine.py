from assist_runtime.runtime.manager import SessionManager
from assist_runtime.runtime.context import ExecutionContext
from assist_runtime.runtime.graph_interface import GraphInterface


class RuntimeEngine:

    def __init__(self):

        self.session_manager = SessionManager()
        self.graph = GraphInterface()

    def start_session(self):

        session = self.session_manager.create_session()
        return session.session_id

    def run(
        self,
        session_id: str,
        input_text: str
    ) -> str:

        session = self.session_manager.get_session(session_id)

        if not session:
            raise ValueError("Invalid session")

        # attach/update runtime context if needed
        if not session.context:
            session.context = ExecutionContext()

        result = self.graph.invoke(
            session=session,
            input_text=input_text
        )

        self.session_manager.update_session(session)

        return result

    def end_session(self, session_id: str):

        self.session_manager.delete_session(session_id)