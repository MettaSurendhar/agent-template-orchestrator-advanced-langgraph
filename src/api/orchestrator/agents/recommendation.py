"""Recommendation Agent — produces a recommendation/decision from validated context.

Replace this for your domain. Example uses: recommend a vendor/supplier, suggest a
resolution for a support case, propose a next action. This agent should be the one
that actually commits to a decision, not just another round of analysis.
"""

from api.orchestrator.agents.base import make_specialist_node
from api.orchestrator.state import OrchestratorState

NAME = "recommendation"
DESCRIPTION = (
    "You produce a concrete recommendation or decision based on the validated context gathered so far. "
    "Commit to a specific recommendation — don't just list options without a stance."
)


def _build_prompt(state: OrchestratorState) -> str:
    return (
        f"User request: {state['user_request']}\n\n"
        f"Validated context: {state['context']}\n\n"
        f"Supervisor's specific instructions for you: {state.get('agent_input', {})}\n\n"
        "Produce your recommendation."
    )


node = make_specialist_node(NAME, DESCRIPTION, _build_prompt)
