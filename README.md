# Multi-Agent Orchestrator Template — Advanced Tier (LangGraph)

[#multi-agent-orchestrator-template-advanced-tier-langgraph](#multi-agent-orchestrator-template-advanced-tier-langgraph)

Production-grade multi-agent orchestration on LangGraph: Postgres-backed durable state, dual-mode JWT/Azure AD SSO auth, per-*team* isolation (not just per-user), and a team-wide review queue. Built for a real organization, not a demo. 🏢🧭

## Which tier do I need?

[#which-tier-do-i-need](#which-tier-do-i-need)

This is one of two advanced-tier options in the Multi-Agent Orchestrator Template family — same production feature set, different framework:

| Tier | Use it when... | Link |
| --- | --- | --- |
| POC | You're prototyping the agent flow itself. In-memory state, minutes to first run. | [agent-template-orchestrator-poc](https://github.com/MettaSurendhar/agent-template-orchestrator-poc) |
| Intermediate | You have real users who need their runs isolated from each other, and runs need to survive a restart. | [agent-template-orchestrator-intermediate](https://github.com/MettaSurendhar/agent-template-orchestrator-intermediate) |
| **Advanced — LangGraph (this repo)** | You're deploying for a real organization and want to build on LangGraph. | — |
| Advanced — AWS Strands | Same production feature set as this repo, built on AWS Strands Agents SDK instead. Pick based on which framework fits your team/stack. | *(pick tier — coming soon)* |

The two advanced tiers are **feature-equivalent by design** — Postgres durability, SSO, team isolation, review queue, all the same. The choice between them is a framework preference, not a capability tradeoff.

## Who is this for?

[#who-is-this-for](#who-is-this-for)

Teams deploying this for real organizational use: multiple teams need to be genuinely isolated from each other (not just multiple users), you need SSO rather than local-only accounts, and a team lead needs to see everything awaiting review across the whole team, not check one run at a time.

## Table of Contents

[#table-of-contents](#table-of-contents)

| Section | Link |
| --- | --- |
| Overview | [Overview](#overview) |
| Repo Structure | [Repo Structure](#repo-structure) |
| Features | [Features](#features) |
| Setup | [Setup](#setup) |
| Usage | [Usage](#usage) |
| Working with AI Coding Agents | [Working with AI Coding Agents](#working-with-ai-coding-agents) |
| Creating a Good README | [Creating a Good README](#creating-a-good-readme) |
| Contribution | [Contribution](#contribution) |
| License | [License](#license) |

---

## Overview

[#overview](#overview)

Users belong to teams (created on registration, or via Azure AD auto-onboarding). Any user on a team can see and resume any run their team started — review is a team responsibility, not an individual one. A team lead can pull up `/reviews/pending` and see every run across the team currently waiting on a human, without knowing individual run IDs in advance.

## Repo Structure

[#repo-structure](#repo-structure)

- **[src/api/orchestrator](./src/api/orchestrator/README.md):** The graph itself — unchanged core logic from the POC/intermediate tiers, now backed by `AsyncPostgresSaver`.
- **[src/api/routers](./src/api/routers/README.md):** `/auth`, `/runs`, `/reviews`, `/audit`.
- **[src/api/schemas](./src/api/schemas/README.md):** Pydantic request/response models.
- **[src/api/utils](./src/api/utils/README.md):** `pg_util.py` — teams, users, run ownership/status cache, audit log, all on Postgres.
- **[src/api/middleware](./src/api/middleware/README.md):** Dual-mode JWT/Azure AD SSO auth.
- **[src/api/client](./src/api/client/README.md):** The structured-JSON LLM call every agent uses.
- **[src/api/exceptions](./src/api/exceptions/README.md):** Error handling pattern.

## Features

[#features](#features)

- **Everything from the intermediate tier**: dynamic Supervisor routing, 5 example specialists, optional per-agent human review, durable state. 🧭
- **Postgres-backed checkpointing** — production-grade concurrent-write handling, verified by a real restart-simulation test against a live Postgres instance. 💾
- **Dual-mode auth**: local JWT (HS256) or Azure AD SSO (RS256 via JWKS) — same middleware, same request, first-time SSO users auto-onboarded into a default team. 🔐
- **Per-*team* isolation, not per-user**: any teammate can see and resume a run — verified by a test with two users on one team and one on another. 👥
- **Team-wide review queue** (`GET /reviews/pending`): see everything awaiting review across the team in one call, sourced from a denormalized status cache so it stays fast at scale. 📋
- **Full audit trail**, team-scoped, queryable via `/audit`. 🧾

## Setup

[#setup](#setup)

See [`setup.md`](./setup.md) — you'll need a Postgres instance (a `docker-compose.yml` for local dev is included).

## Usage

[#usage](#usage)

See [`usage.md`](./usage.md) for the full register → start → team-wide review → resume → audit flow.

## Working with AI Coding Agents

[#working-with-ai-coding-agents](#working-with-ai-coding-agents)

See [`CLAUDE.md`](./CLAUDE.md).

## Creating a Good README

[#creating-a-good-readme](#creating-a-good-readme)

See [`good-readme.md`](./good-readme.md).

## Contribution

[#contribution](#contribution)

See [`contributing.md`](./contributing.md).

## License

[#license](#license)

MIT — see [LICENSE](./LICENSE).

---

## [🌟 Star this Repository](#)
