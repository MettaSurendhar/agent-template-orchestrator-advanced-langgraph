# src/api/middleware

[#src-api-middleware](#src-api-middleware)

## What's here

- `auth_middleware.py` — dual-mode verification. Inspects the token's `alg` header: `HS256` is verified against the local `JWT_SECRET` and looked up in the `users` table by `user_id`; `RS256` is verified against the Azure AD tenant's JWKS endpoint and resolved (or auto-created) by email via `pg_util.get_or_create_sso_user()`. Both paths attach `request.state.user_id` and `request.state.team_id`.

## Conventions

- This is the **only** place token verification happens — don't re-verify in individual routers.
- `request.state.team_id` (not `user_id`) is what gates run-scoped endpoints — see `routers/runs.py`'s `_require_team_ownership()`. `user_id` is kept for attribution (who started/resumed a run), not for isolation.
- If you add a third auth mode, follow the existing `if alg == ... elif alg == ...` pattern and make sure it still resolves to both `user_id` and `team_id` before calling `call_next` — every downstream router assumes both are present.
