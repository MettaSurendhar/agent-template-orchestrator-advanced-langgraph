"""Supervisor — the node that makes this an *orchestrator* rather than a fixed pipeline.

Every turn, it looks at the user request, what's been executed, and the accumulated
context, then decides which specialist runs next (or that the run is done). This is the
one node in the graph you generally should NOT need to fork per-domain — only the
`AGENT_REGISTRY` it reads from changes.
"""

import json

from api.client.llm_client import generate_structured
from api.exceptions.custom_exceptions import APIException, ErrorCode
from api.orchestrator.agents.registry import AGENT_REGISTRY
from api.orchestrator.state import OrchestratorState

SYSTEM_PROMPT = """You are the Supervisor of a multi-agent workflow. Given a user request, the agents \
available, which have already run, and the context gathered so far, decide which single agent should run \
next — or that the workflow is complete.

Respond with ONLY a JSON object of this shape, no markdown fences, no commentary:
{
  "next_agent": "<agent_name from the available list, or STOP if the workflow is complete>",
  "rationale": "one sentence explaining this choice",
  "agent_input": { ... any specific instructions/focus for that agent, or {} ... }
}

Don't re-run an agent that's already executed unless there's a clear reason to (e.g. validation failed and \
the upstream agent needs to redo its work). Choose STOP once you have enough context to produce a useful \
final summary — you don't need to run every available agent."""


def node(state: OrchestratorState) -> dict:
    """Decide the next agent to run."""
    agent_descriptions = "\n".join(f"- {name}: {info['description']}" for name, info in AGENT_REGISTRY.items())

    user_prompt = (
        f"User request: {state['user_request']}\n\n"
        f"Available agents:\n{agent_descriptions}\n\n"
        f"Already executed: {state['executed_agents']}\n\n"
        f"Context gathered so far:\n{json.dumps(state['context'], indent=2)}\n\n"
        "Decide the next step."
    )

    try:
        plan = generate_structured(SYSTEM_PROMPT, user_prompt)
    except APIException:
        # Fail safe: stop the run rather than looping forever on a broken supervisor call.
        return {
            "next_agent": "STOP",
            "rationale": "Supervisor call failed; stopping the workflow.",
            "agent_input": {},
            "audit_trail": [{"agent": "supervisor", "action": "failed"}],
        }

    next_agent = plan.get("next_agent", "STOP")

    if next_agent != "STOP" and next_agent not in AGENT_REGISTRY:
        raise APIException(
            status_code=500,
            error_code=ErrorCode.SUPERVISOR_FAILED,
            message=f"Supervisor chose an unknown agent: {next_agent}",
            details=f"Valid agents: {list(AGENT_REGISTRY.keys())}",
        )

    return {
        "next_agent": next_agent,
        "rationale": plan.get("rationale", ""),
        "agent_input": plan.get("agent_input", {}),
        "audit_trail": [{"agent": "supervisor", "action": "routed", "decision": next_agent, "rationale": plan.get("rationale", "")}],
    }
