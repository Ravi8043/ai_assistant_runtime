from assist_runtime.runtime.session import Session


class SessionManager:
    #constructor
    def __init__(self):

        self.sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        #creates a session obj with session id
        session = Session()

        #key value pair storing the session
        self.sessions[
            session.session_id
        ] = session

        return session

    #fetch sessions
    def get_session(
        self,
        session_id: str
    ) -> Session | None:
        
        #dict method get used to fetch session id
        return self.sessions.get(
            session_id
        )

    def delete_session(
        self,
        session_id: str
    ) -> None:

        self.sessions.pop(
            session_id,
            None
        )

    #override fields in session then call this function 
    def update_session(
        self,
        session: Session
    ) -> None:

        self.sessions[
            session.session_id
        ] = session