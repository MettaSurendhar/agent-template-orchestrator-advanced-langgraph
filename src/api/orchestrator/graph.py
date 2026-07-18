"""Builds the orchestration graph: supervisor <-> specialists loop, ending in summarizer.

    START -> supervisor -> (one of the registered specialists, or summarizer if STOP)
    specialist -> supervisor (loop), unless a human rejected it mid-review -> END
    summarizer -> END

The loop is capped by `settings.max_turns` as a safety net against a supervisor that
never chooses STOP — LangGraph itself doesn't know about that cap, so it's enforced by
counting `executed_agents` in the routing function.

Unlike the POC tier, this tier does NOT build its own checkpointer or hold a module-level
compiled graph singleton — the checkpointer (`AsyncSqliteSaver`) has its own async
lifecycle tied to a database connection, which needs to be opened once at app startup and
closed at shutdown. See `app.py`'s lifespan handler, which calls `build_graph(checkpointer)`
once and stores the result on `app.state.graph`.
"""

from langgraph.graph import END, START, StateGraph

from api import settings
from api.orchestrator.agents import summarizer, supervisor
from api.orchestrator.agents.registry import AGENT_REGISTRY
from api.orchestrator.state import OrchestratorState


def _route_from_supervisor(state: OrchestratorState) -> str:
    if len(state["executed_agents"]) >= settings.max_turns:
        return "summarizer"
    if state["next_agent"] == "STOP":
        return "summarizer"
    return state["next_agent"]


def _route_from_specialist(state: OrchestratorState) -> str:
    if state["status"] == "rejected":
        return END
    return "supervisor"


def build_graph(checkpointer):
    """Construct and compile the orchestration graph with the given checkpointer."""
    graph = StateGraph(OrchestratorState)

    graph.add_node("supervisor", supervisor.node)
    graph.add_node("summarizer", summarizer.node)
    for name, info in AGENT_REGISTRY.items():
        graph.add_node(name, info["node"])

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor", _route_from_supervisor, {**{name: name for name in AGENT_REGISTRY}, "summarizer": "summarizer"}
    )

    for name in AGENT_REGISTRY:
        graph.add_conditional_edges(name, _route_from_specialist, {"supervisor": "supervisor", END: END})

    graph.add_edge("summarizer", END)

    return graph.compile(checkpointer=checkpointer)
