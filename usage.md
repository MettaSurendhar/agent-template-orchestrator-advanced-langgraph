# Usage

[#usage](#usage)

## 1. Register (creates or joins a team)

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "a-real-password", "team_name": "Procurement Team"}'
```

```json
{ "access_token": "eyJ...", "token_type": "bearer", "user_id": "user-...", "team_id": "team-..." }
```

A second person registering with the same `team_name` joins the same team and can see the first person's runs:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "carol@example.com", "password": "another-password", "team_name": "Procurement Team"}'
```

## 2. Start a run

```bash
curl -X POST http://localhost:8000/runs \
  -H "Authorization: Bearer <alice's token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Evaluate whether we should proceed with this vendor proposal.",
    "review_agents": ["recommendation"]
  }'
```

```json
{
  "run_id": "run-8a2b1c3d4e5f",
  "status": "paused",
  "pending_review": {"agent": "recommendation", "output": { "...": "..." }},
  "...": "..."
}
```

## 3. See everything your team has waiting on review (not just this one run)

```bash
curl http://localhost:8000/reviews/pending -H "Authorization: Bearer <carol's token>"
```

```json
{
  "reviews": [
    {
      "run_id": "run-8a2b1c3d4e5f",
      "user_request": "Evaluate whether we should proceed with this vendor proposal.",
      "started_by_user_id": "user-alice-id",
      "pending_review_agent": "recommendation",
      "pending_review_output": { "...": "..." },
      "updated_at": "2026-07-18T09:00:00+00:00"
    }
  ]
}
```

Carol didn't start this run — she can see it because she's on the same team.

## 4. Carol resumes it (not the original starter)

```bash
curl -X POST http://localhost:8000/runs/run-8a2b1c3d4e5f/resume \
  -H "Authorization: Bearer <carol's token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "approve"}'
```

This succeeds — review is a team responsibility at this tier, not restricted to whoever clicked "start."

## 5. List your team's runs

```bash
curl http://localhost:8000/runs -H "Authorization: Bearer <alice's token>"
```

```json
{
  "runs": [
    {
      "run_id": "run-8a2b1c3d4e5f",
      "user_request": "Evaluate whether we should proceed...",
      "started_by_user_id": "user-alice-id",
      "status": "completed",
      "created_at": "2026-07-18T09:00:00+00:00"
    }
  ]
}
```

## 6. Check the team's audit log

```bash
curl http://localhost:8000/audit -H "Authorization: Bearer <alice's token>"
```

## 7. What a different team sees

A user on a different team gets a 404 for `run-8a2b1c3d4e5f` — same as if it didn't exist:

```json
{ "error_code": "RUN_NOT_FOUND", "message": "No run found: run-8a2b1c3d4e5f", "details": null }
```

And that run never appears in their `/reviews/pending` or `/runs` list.

## 8. Azure AD SSO (if configured)

Skip `/auth/register`/`/auth/login` entirely — obtain a token from your Azure AD app as normal (standard OAuth2/OIDC flow, outside the scope of this API), then use it directly:

```bash
curl http://localhost:8000/runs -H "Authorization: Bearer <azure-ad-token>"
```

First-time SSO users are auto-onboarded into `DEFAULT_TEAM_ID` — no registration step needed.
