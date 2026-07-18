"""Analysis Agent — analyzes structured input data relevant to the domain.

Replace this for your domain. Example uses: analyze a document/dataset attached to the
request, evaluate a technical spec, run domain-specific calculations. Typically depends
on the Research agent's output already being in context.
"""

from api.orchestrator.agents.base import make_specialist_node
from api.orchestrator.state import OrchestratorState

NAME = "analysis"
DESCRIPTION = (
    "You perform the core domain-specific analysis for this request, building on whatever context has "
    "already been gathered. You produce concrete findings, not just a restatement of the request."
)


def _build_prompt(state: OrchestratorState) -> str:
    return (
        f"User request: {state['user_request']}\n\n"
        f"Context gathered so far: {state['context']}\n\n"
        f"Supervisor's specific instructions for you: {state.get('agent_input', {})}\n\n"
        "Perform your analysis and report concrete findings."
    )


node = make_specialist_node(NAME, DESCRIPTION, _build_prompt)
