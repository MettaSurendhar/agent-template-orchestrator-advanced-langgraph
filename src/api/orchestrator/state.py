"""The shared state every node in the graph reads from and writes to.

`executed_agents` and `audit_trail` use `operator.add` as their reducer, so each node
can return just its own new entries and LangGraph appends them, rather than every node
needing to know and repeat the full running list.
"""

import operator
from typing import Annotated, TypedDict


class OrchestratorState(TypedDict):
    """State for one orchestration run, persisted by the LangGraph checkpointer."""

    run_id: str
    team_id: str
    user_id: str  # the user who started the run, for attribution
    user_request: str
    artifacts: dict
    review_agents: list[str]  # agent names that should pause for human review before continuing

    context: dict  # agent_name -> that agent's structured output, accumulated as the run progresses
    executed_agents: Annotated[list[str], operator.add]
    audit_trail: Annotated[list[dict], operator.add]

    next_agent: str  # set by the supervisor each turn
    rationale: str  # supervisor's stated reason for that choice
    agent_input: dict  # supervisor's specific instructions for the chosen agent

    status: str  # "running" | "paused" | "completed" | "rejected" | "failed"
    final_summary: str
