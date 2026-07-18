"""Validation Agent — checks consistency/completeness of prior agents' outputs.

Replace this for your domain. Example uses: check that an analysis is internally
consistent, flag missing required fields, verify a recommendation doesn't violate a
known constraint. This agent's job is to catch problems before they propagate further,
not to redo the upstream work.
"""

from api.orchestrator.agents.base import make_specialist_node
from api.orchestrator.state import OrchestratorState

NAME = "validation"
DESCRIPTION = (
    "You check the consistency and completeness of what prior agents have produced so far. "
    "You flag gaps, contradictions, or violations of known constraints — you do not redo their analysis."
)


def _build_prompt(state: OrchestratorState) -> str:
    return (
        f"User request: {state['user_request']}\n\n"
        f"Context to validate: {state['context']}\n\n"
        f"Supervisor's specific instructions for you: {state.get('agent_input', {})}\n\n"
        "Validate the above and report any issues found."
    )


node = make_specialist_node(NAME, DESCRIPTION, _build_prompt)
