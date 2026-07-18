"""Tests the graph directly (not through the API) with the real AsyncPostgresSaver
checkpointer — including a simulated process restart: a brand new AsyncPostgresSaver
instance pointed at the same database must be able to resume a paused run.
"""

import uuid
from unittest.mock import patch

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from api import settings
from api.orchestrator.graph import build_graph

supervisor_calls = {"n": 0}


def _fake_generate_structured(system_prompt: str, user_prompt: str) -> dict:
    if "Supervisor" in system_prompt:
        supervisor_calls["n"] += 1
        if supervisor_calls["n"] == 1:
            return {"next_agent": "research", "rationale": "r1", "agent_input": {}}
        return {"next_agent": "STOP", "rationale": "done", "agent_input": {}}
    elif "Summarizer" in system_prompt:
        return {"final_summary": "PG persisted summary."}
    return {"summary": "work", "structured_output": {}, "warnings": []}


def _initial_state(run_id: str, review_agents: list[str]) -> dict:
    return {
        "run_id": run_id,
        "team_id": "team-test",
        "user_id": "user-test",
        "user_request": "test",
        "artifacts": {},
        "review_agents": review_agents,
        "context": {},
        "executed_agents": [],
        "audit_trail": [],
        "next_agent": "",
        "rationale": "",
        "agent_input": {},
        "status": "running",
        "final_summary": "",
    }


@pytest.mark.asyncio
async def test_state_survives_a_new_checkpointer_instance():
    """Simulates an app restart: state written by one AsyncPostgresSaver instance must be
    readable — and resumable — by a completely separate instance against the same database."""
    supervisor_calls["n"] = 0
    thread_id = f"restart-run-{uuid.uuid4().hex[:8]}"

    with (
        patch("api.orchestrator.agents.base.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.supervisor.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.summarizer.generate_structured", side_effect=_fake_generate_structured),
    ):
        config = {"configurable": {"thread_id": thread_id}}

        # "Process 1": start the run, pause for review.
        async with AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer:
            await checkpointer.setup()
            graph = build_graph(checkpointer)
            await graph.ainvoke(_initial_state(thread_id, ["research"]), config=config)
            snapshot = await graph.aget_state(config)
            assert snapshot.next, "should be paused"

        # "Process 2": brand new checkpointer, same database — simulates a restart.
        async with AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer:
            graph = build_graph(checkpointer)
            snapshot = await graph.aget_state(config)
            assert snapshot.next, "paused state should have survived the simulated restart"
            assert snapshot.tasks[0].interrupts[0].value["agent"] == "research"

            await graph.ainvoke(
                Command(resume={"action": "approve", "edited_output": None, "reason": None}), config=config
            )
            snapshot = await graph.aget_state(config)
            assert not snapshot.next
            assert snapshot.values["status"] == "completed"
            assert snapshot.values["final_summary"] == "PG persisted summary."


@pytest.mark.asyncio
async def test_reject_during_review_stops_the_run():
    supervisor_calls["n"] = 0
    thread_id = f"reject-run-{uuid.uuid4().hex[:8]}"

    with (
        patch("api.orchestrator.agents.base.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.supervisor.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.summarizer.generate_structured", side_effect=_fake_generate_structured),
    ):
        config = {"configurable": {"thread_id": thread_id}}

        async with AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer:
            await checkpointer.setup()
            graph = build_graph(checkpointer)
            await graph.ainvoke(_initial_state(thread_id, ["research"]), config=config)
            await graph.ainvoke(
                Command(resume={"action": "reject", "edited_output": None, "reason": "bad data"}), config=config
            )
            snapshot = await graph.aget_state(config)
            assert not snapshot.next
            assert snapshot.values["status"] == "rejected"
