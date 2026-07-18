"""Estimation Agent — produces a quantified output (cost, score, risk, timeline...).

Replace this for your domain. Example uses: cost estimate, risk score, confidence
rating, timeline projection. Whatever number(s) your domain needs attached to the
recommendation before the run is summarized.
"""

from api.orchestrator.agents.base import make_specialist_node
from api.orchestrator.state import OrchestratorState

NAME = "estimation"
DESCRIPTION = (
    "You produce a quantified estimate (cost, score, risk rating, timeline — whatever fits the domain) "
    "based on the recommendation and context so far. Always include the actual number(s), not just a range description."
)


def _build_prompt(state: OrchestratorState) -> str:
    return (
        f"User request: {state['user_request']}\n\n"
        f"Full context so far: {state['context']}\n\n"
        f"Supervisor's specific instructions for you: {state.get('agent_input', {})}\n\n"
        "Produce your quantified estimate."
    )


node = make_specialist_node(NAME, DESCRIPTION, _build_prompt)
