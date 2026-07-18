"""Summarizer — synthesizes the full run into one final, user-facing output.

Runs once, after the supervisor decides to STOP. Not a specialist (doesn't go through
`make_specialist_node`) since it doesn't participate in the routing loop or support
per-agent review — it's always the last thing that happens in a successful run.
"""

import json

from api.client.llm_client import generate_structured
from api.orchestrator.state import OrchestratorState

SYSTEM_PROMPT = """You are the Summarizer for a multi-agent workflow that has just completed. Synthesize \
everything the specialist agents produced into one clear, user-facing summary.

Respond with ONLY a JSON object of this shape, no markdown fences, no commentary:
{
  "final_summary": "a clear, complete summary of the outcome, written for the person who made the request"
}"""


def node(state: OrchestratorState) -> dict:
    """Produce the final summary of the run."""
    user_prompt = (
        f"User request: {state['user_request']}\n\n"
        f"Agents executed: {state['executed_agents']}\n\n"
        f"Full context:\n{json.dumps(state['context'], indent=2)}\n\n"
        "Write the final summary."
    )

    result = generate_structured(SYSTEM_PROMPT, user_prompt)

    return {
        "final_summary": result.get("final_summary", ""),
        "status": "completed",
        "audit_trail": [{"agent": "summarizer", "action": "completed"}],
    }
