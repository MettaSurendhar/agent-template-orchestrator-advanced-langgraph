"""End-to-end tests through the actual FastAPI app: team-based registration, team-wide
run visibility (any teammate can see/resume a run, not just its starter), cross-team
isolation, and the review queue endpoint.
"""

import uuid
from unittest.mock import patch

supervisor_calls = {"n": 0}


def _fake_generate_structured(system_prompt: str, user_prompt: str) -> dict:
    if "Supervisor" in system_prompt:
        supervisor_calls["n"] += 1
        if supervisor_calls["n"] == 1:
            return {"next_agent": "research", "rationale": "r1", "agent_input": {}}
        return {"next_agent": "STOP", "rationale": "done", "agent_input": {}}
    elif "Summarizer" in system_prompt:
        return {"final_summary": "E2E summary."}
    return {"summary": "e2e work", "structured_output": {"x": 1}, "warnings": []}


def _register(client, email: str, team_name: str) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": "a-real-password-123", "team_name": team_name})
    assert r.status_code == 200, r.text
    return r.json()


def test_team_wide_visibility_and_cross_team_isolation_and_review_queue():
    supervisor_calls["n"] = 0
    unique = uuid.uuid4().hex[:8]

    with (
        patch("api.orchestrator.agents.base.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.supervisor.generate_structured", side_effect=_fake_generate_structured),
        patch("api.orchestrator.agents.summarizer.generate_structured", side_effect=_fake_generate_structured),
    ):
        from fastapi.testclient import TestClient

        from app import app

        with TestClient(app) as client:
            assert client.get("/ping").status_code == 200

            # Two users on the SAME team.
            alice = _register(client, f"alice-{unique}@example.com", f"team-alpha-{unique}")
            carol = _register(client, f"carol-{unique}@example.com", f"team-alpha-{unique}")
            assert alice["team_id"] == carol["team_id"], "same team_name should resolve to the same team_id"

            # One user on a DIFFERENT team.
            bob = _register(client, f"bob-{unique}@example.com", f"team-beta-{unique}")
            assert bob["team_id"] != alice["team_id"]

            headers_alice = {"Authorization": f"Bearer {alice['access_token']}"}
            headers_carol = {"Authorization": f"Bearer {carol['access_token']}"}
            headers_bob = {"Authorization": f"Bearer {bob['access_token']}"}

            # Alice starts a run that pauses for review.
            r = client.post(
                "/runs", json={"user_request": "Evaluate X", "review_agents": ["research"]}, headers=headers_alice
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["status"] == "paused"
            run_id = data["run_id"]

            # Carol (same team) CAN see it, even though she didn't start it.
            r = client.get(f"/runs/{run_id}", headers=headers_carol)
            assert r.status_code == 200, r.text

            # Bob (different team) CANNOT see or resume it.
            assert client.get(f"/runs/{run_id}", headers=headers_bob).status_code == 404
            assert client.post(f"/runs/{run_id}/resume", json={"action": "approve"}, headers=headers_bob).status_code == 404

            # The review queue shows it for Alice's/Carol's team...
            r = client.get("/reviews/pending", headers=headers_alice)
            assert r.status_code == 200, r.text
            pending_run_ids = {item["run_id"] for item in r.json()["reviews"]}
            assert run_id in pending_run_ids

            # ...but NOT for Bob's team.
            r = client.get("/reviews/pending", headers=headers_bob)
            assert r.status_code == 200
            assert run_id not in {item["run_id"] for item in r.json()["reviews"]}

            # Carol (not the original starter) resumes it.
            r = client.post(f"/runs/{run_id}/resume", json={"action": "approve"}, headers=headers_carol)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["status"] == "completed"
            assert data["final_summary"] == "E2E summary."

            # It's now gone from the review queue.
            r = client.get("/reviews/pending", headers=headers_alice)
            assert run_id not in {item["run_id"] for item in r.json()["reviews"]}

            # It shows up in the team's run list with the correct starter attribution.
            r = client.get("/runs", headers=headers_alice)
            assert r.status_code == 200
            matching = [run for run in r.json()["runs"] if run["run_id"] == run_id]
            assert matching and matching[0]["started_by_user_id"] == alice["user_id"]
            assert matching[0]["status"] == "completed"

            # Audit log has entries for the team.
            r = client.get("/audit", headers=headers_alice)
            assert r.status_code == 200
            event_types = {e["event_type"] for e in r.json()["events"]}
            assert "RUN_STARTED" in event_types
            assert "RUN_RESUMED" in event_types
            assert "RUN_COMPLETED" in event_types


def test_unauthenticated_request_rejected():
    from fastapi.testclient import TestClient

    from app import app

    with TestClient(app) as client:
        r = client.post("/runs", json={"user_request": "test"})
        assert r.status_code == 401
        assert r.json()["error_code"] == "UNAUTHORIZED"


def test_duplicate_registration_rejected():
    from fastapi.testclient import TestClient

    from app import app

    unique = uuid.uuid4().hex[:8]
    with TestClient(app) as client:
        email = f"dup-{unique}@example.com"
        assert client.post("/auth/register", json={"email": email, "password": "pw12345678", "team_name": f"t-{unique}"}).status_code == 200
        r = client.post("/auth/register", json={"email": email, "password": "pw12345678", "team_name": f"t-{unique}"})
        assert r.status_code == 409
