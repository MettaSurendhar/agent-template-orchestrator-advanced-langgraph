"""Research Agent — gathers/classifies context on the incoming request.

Replace this for your domain. Example uses: classify a support ticket's category,
look up a customer's account tier, pull relevant background on a topic. This is
typically the first specialist the supervisor picks, since later agents usually
depend on its output.
"""

from api.orchestrator.agents.base import make_specialist_node
from api.orchestrator.state import OrchestratorState

NAME = "research"
DESCRIPTION = (
    "You gather and classify background context relevant to the request before deeper analysis happens. "
    "You do not make decisions — you establish facts and categorize the request for the agents after you."
)


def _build_prompt(state: OrchestratorState) -> str:
    return (
        f"User request: {state['user_request']}\n\n"
        f"Artifacts provided: {state['artifacts']}\n\n"
        f"Supervisor's specific instructions for you: {state.get('agent_input', {})}\n\n"
        "Gather and classify the relevant context for this request."
    )


node = make_specialist_node(NAME, DESCRIPTION, _build_prompt)
