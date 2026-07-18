"""The list of specialist agents the supervisor can choose from.

Add/remove/rename agents here and the supervisor's routing options update automatically
— you don't need to touch `supervisor.py` or `graph.py` for a simple agent swap. If you
add an agent, also register it as a graph node in `graph.py`.
"""

from api.orchestrator.agents import analysis, estimation, recommendation, research, validation

AGENT_REGISTRY = {
    research.NAME: {"description": research.DESCRIPTION, "node": research.node},
    analysis.NAME: {"description": analysis.DESCRIPTION, "node": analysis.node},
    validation.NAME: {"description": validation.DESCRIPTION, "node": validation.node},
    recommendation.NAME: {"description": recommendation.DESCRIPTION, "node": recommendation.node},
    estimation.NAME: {"description": estimation.DESCRIPTION, "node": estimation.node},
}
