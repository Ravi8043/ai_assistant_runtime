from assist_runtime.runtime.session import Session


class GraphInterface:

    def invoke(
        self,
        session: Session,
        input_text: str
    ) -> str:

        """
        Entry point to graph execution.
        (No LLM yet — just structured flow placeholder)
        """

        session.add_message("user", input_text)

        # STEP 1: fake planner here you can call an llm to plan the next steps
        plan = f"understood intent: {input_text}"

        # STEP 2: fake execution here you can call an llm to execute the plan
        result = f"[graph executed] {plan}"

        # store assistant response
        session.add_message("assistant", result)

        return result

        # # attach input into graph state
    #     state = GraphState(
    #         session=session,
    #         input_text=input_text,
    #         result=None
    #     )

    #     # execute full graph
    #     final_state = self.graph.run(state)

    #     # return final output from state
    #     session.add_message("assistant", result)
    #     return final_state.result