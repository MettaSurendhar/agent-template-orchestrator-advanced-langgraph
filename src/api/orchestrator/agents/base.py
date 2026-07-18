"""Factory for building a specialist agent node.

Every specialist in `agents/` (research.py, analysis.py, validation.py,
recommendation.py, estimation.py) is a thin domain-specific prompt plumbed through
`make_specialist_node`. This is deliberate: when you fork this template for your own
domain, the file you edit per agent is small and focused on "what should this agent
ask the LLM," not on graph mechanics, review-interrupt handling, or audit logging —
that machinery lives here, once, and stays correct across every fork.
"""

from collections.abc import Callable

from langgraph.types import interrupt

from api.client.llm_client import generate_structured
from api.orchestrator.state import OrchestratorState

SYSTEM_PROMPT_TEMPLATE = """You are the {agent_name} in a multi-agent workflow. {agent_description}

Respond with ONLY a JSON object of this shape, no markdown fences, no commentary:
{{
  "summary": "one or two sentence summary of what you found/decided",
  "structured_output": {{ ... whatever fields make sense for your analysis ... }},
  "warnings": ["any caveats or issues worth flagging, or an empty list"]
}}"""


def make_specialist_node(
    agent_name: str, agent_description: str, build_user_prompt: Callable[[OrchestratorState], str]
) -> Callable[[OrchestratorState], dict]:
    """Return a LangGraph node function for a specialist agent.

    `build_user_prompt` receives the current state and returns the user-facing prompt
    text — this is the one thing that's actually domain-specific per agent.
    """

    def node(state: OrchestratorState) -> dict:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(agent_name=agent_name, agent_description=agent_description)
        user_prompt = build_user_prompt(state)

        output = generate_structured(system_prompt, user_prompt)

        audit_entries = [{"agent": agent_name, "action": "completed", "summary": output.get("summary", "")}]

        # Optional human-in-the-loop: pause after this agent if it's in review_agents.
        if agent_name in state.get("review_agents", []):
            decision = interrupt({"agent": agent_name, "output": output})
            # `decision` is whatever the caller resumes with — see routers/runs.py's /resume endpoint.
            action = decision.get("action", "approve")

            if action == "reject":
                audit_entries.append(
                    {"agent": agent_name, "action": "rejected", "reason": decision.get("reason", "")}
                )
                return {
                    "status": "rejected",
                    "audit_trail": audit_entries,
                }

            if action == "edit":
                output = decision.get("edited_output", output)
                audit_entries.append({"agent": agent_name, "action": "edited"})
            else:
                audit_entries.append({"agent": agent_name, "action": "approved"})

        return {
            "context": {**state["context"], agent_name: output},
            "executed_agents": [agent_name],
            "audit_trail": audit_entries,
        }

    return node
