# src/api/client

[#src-api-client](#src-api-client)

## What's here

- **`llm_client.py`** — `generate_structured(system_prompt, user_prompt) -> dict`, the single function every agent (Supervisor, specialists, Summarizer) uses to talk to an LLM. Enforces JSON-only output: strips markdown fences, extracts the outermost `{...}` block, and retries once with a sterner instruction if parsing fails on the first attempt. Raises `APIException(AGENT_FAILED)` if it still can't parse after the retry.

## Conventions

- Every agent calls `generate_structured`, never a provider SDK directly — this is what keeps `LLM_PROVIDER=openai|bedrock` a one-line config change across every agent at once.
- If you add a third provider, add a `_generate_<provider>` function following the existing pattern and a branch in `_generate_text`'s if/elif — don't change `generate_structured`'s signature or JSON-handling logic, since every agent depends on that contract staying stable.
