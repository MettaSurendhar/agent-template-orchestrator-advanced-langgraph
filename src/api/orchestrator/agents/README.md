# src/api/orchestrator/agents

[#src-api-orchestrator-agents](#src-api-orchestrator-agents)

## What's here

- **`base.py`** — `make_specialist_node()`, the factory every specialist is built from. Handles: calling the LLM for structured output, the optional review-interrupt, and audit-trail entries. **Edit this only for changes that should apply to every specialist across every fork of this template.**
- **`registry.py`** — `AGENT_REGISTRY`, mapping agent name -> `{description, node}`. This is what the Supervisor reads to know its routing options, and what `graph.py` reads to wire the graph. Add/remove/rename a specialist here.
- **`supervisor.py`** — the dynamic router. Reads `AGENT_REGISTRY` to build its prompt's list of available agents; you generally don't need to touch this file when forking for a new domain — only its dependency (`registry.py`) changes.
- **`summarizer.py`** — runs once, after the Supervisor decides `STOP`. Synthesizes `context` into `final_summary`.
- **`research.py`, `analysis.py`, `validation.py`, `recommendation.py`, `estimation.py`** — the 5 example specialists. Each is a `NAME`, a `DESCRIPTION` (used both in its own system prompt and in the Supervisor's routing prompt), and a `_build_prompt(state)` function. **These are exactly what you replace when forking for your own domain** — see `CLAUDE.md`'s checklist.

## Conventions

- A specialist file should contain domain logic only (what to ask the LLM, given the state). It should never handle review/interrupt logic, audit entries, or state merging directly — that's `base.py`'s job, and duplicating it per-agent is how forks drift and get inconsistent behavior.
- `DESCRIPTION` is read by the Supervisor to decide whether to route to this agent — write it as a routing hint ("you do X, given Y"), not just a human-readable label.
- `_build_prompt(state)` should read from `state["context"]` for what previous agents found, and `state["agent_input"]` for the Supervisor's specific instructions for this turn — don't ignore `agent_input`, since that's how the Supervisor gives a specialist targeted direction rather than a generic re-run.
