"""LLM calls for the orchestrator: plain text generation and structured (JSON) generation.

Every agent node — supervisor and specialists alike — goes through `generate_structured`,
which enforces JSON-only output and retries once on a parse failure. This is the one
piece of discipline worth keeping across every tier of this template: an agent that
returns malformed JSON should fail loudly and get one retry, not silently corrupt the
graph state.
"""

import json
import re

from api import settings
from api.exceptions.custom_exceptions import APIException, ErrorCode


def generate_structured(system_prompt: str, user_prompt: str) -> dict:
    """Call the configured LLM and parse its response as JSON. Retries once on parse failure."""
    for attempt in range(2):
        raw = _generate_text(system_prompt, user_prompt)
        parsed = _extract_json(raw)
        if parsed is not None:
            return parsed
        if attempt == 0:
            user_prompt = (
                f"{user_prompt}\n\nYour previous response could not be parsed as JSON. "
                "Respond with ONLY a valid JSON object, no markdown fences, no commentary."
            )

    raise APIException(
        status_code=500,
        error_code=ErrorCode.AGENT_FAILED,
        message="LLM did not return parseable JSON after a retry.",
        details=raw[:500] if raw else None,
    )


def _generate_text(system_prompt: str, user_prompt: str) -> str:
    try:
        if settings.llm_provider == "openai":
            return _generate_openai(system_prompt, user_prompt)
        elif settings.llm_provider == "bedrock":
            return _generate_bedrock(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    except APIException:
        raise
    except Exception as e:
        raise APIException(
            status_code=500, error_code=ErrorCode.AGENT_FAILED, message="LLM call failed.", details=str(e)
        ) from e


def _generate_openai(system_prompt: str, user_prompt: str) -> str:
    if not settings.openai_api_key:
        raise APIException(
            status_code=500,
            error_code=ErrorCode.AGENT_FAILED,
            message="OPENAI_API_KEY is not set.",
            details="Set it in .env, or switch LLM_PROVIDER=bedrock.",
        )

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=settings.llm_temperature,
    )
    return response.choices[0].message.content.strip()


def _generate_bedrock(system_prompt: str, user_prompt: str) -> str:
    import boto3

    if not settings.bedrock_model_id:
        raise APIException(
            status_code=500,
            error_code=ErrorCode.AGENT_FAILED,
            message="BEDROCK_MODEL_ID is not set.",
            details="Set it in .env, or switch LLM_PROVIDER=openai.",
        )

    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    response = client.converse(
        modelId=settings.bedrock_model_id,
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        system=[{"text": system_prompt}],
        inferenceConfig={"temperature": settings.llm_temperature},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction: strips markdown fences, finds the outermost {...} block."""
    if not text:
        return None

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return None
