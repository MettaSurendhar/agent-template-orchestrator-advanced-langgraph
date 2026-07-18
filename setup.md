# Setup

[#setup](#setup)

## Prerequisites

- Python 3.10+ (3.12 recommended)
- A Postgres instance (16+ recommended) — `docker-compose.yml` included for local dev
- AWS credentials with Bedrock access (default LLM provider at this tier), or an OpenAI API key
- Optional: an Azure AD app registration, if you want SSO in addition to local auth

## 1. Start Postgres

```bash
docker compose up -d postgres
```

Or point `DATABASE_URL` at any existing Postgres 16+ instance.

## 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

## 3. Configure

```bash
cp .env.example .env
```

Set `JWT_SECRET` to a real random value. Set `DATABASE_URL` if not using the default local Docker setup. Set either `BEDROCK_MODEL_ID` + AWS credentials, or `OPENAI_API_KEY` + `LLM_PROVIDER=openai`.

**Azure AD SSO is optional** — leave `AZURE_TENANT_ID`/`AZURE_CLIENT_ID` blank to run local-auth-only. To enable it, register an app in Azure AD, note its tenant ID and client ID, and set both env vars. First-time SSO logins are auto-onboarded into `DEFAULT_TEAM_ID`.

## 4. Run

```bash
make run
```

On first startup, the app creates its own tables (`teams`, `users`, `orchestrator_runs`, `audit_log`) and LangGraph's checkpoint tables automatically — no manual migration step needed for a fresh database.

## 5. Verify

```bash
curl http://localhost:8000/ping
# {"status": "OK"}
```

## 6. Run the tests

```bash
make test
```

**These tests run against a real Postgres instance** (via `tests/conftest.py`, pointed at a test database automatically — make sure Postgres is running first). This tier's whole value proposition — durable state, team isolation — isn't honestly testable against a mock, so the test suite doesn't try to fake it.

## Docker

```bash
docker compose up -d postgres
docker build -t orchestrator-advanced-langgraph .
docker run --env-file .env -p 8000:8000 --network host orchestrator-advanced-langgraph
```

(`--network host` is the simplest way to reach the Compose Postgres container from a separately-run container in local dev; in a real deployment your Postgres and app would typically share a Docker network or the app would point at a managed Postgres instance instead.)
