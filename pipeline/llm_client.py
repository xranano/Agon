import json
import re
import time
from typing import Any, Dict, Type, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    BadRequestError,
    LengthFinishReasonError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

# Single source of truth for env/config (config.py loads .env once).
from config import MAX_RETRIES, OPENAI_API_KEY, OPENAI_MODEL

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your local .env file.")
client = OpenAI(api_key=OPENAI_API_KEY)
ModelT = TypeVar("ModelT", bound=BaseModel)

# Transient errors worth retrying with exponential backoff.
_TRANSIENT_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)

# Reasoning models (o-series, gpt-5*) accept reasoning/verbosity controls; other
# models reject them. We try with the controls and drop them once if rejected.
_MODEL_SUPPORTS_REASONING = True


def _with_backoff(make_request, *, retries: int, label: str):
    """Call an OpenAI request, retrying transient errors with exponential backoff."""

    delay = 2.0
    last_error: Exception | None = None
    for attempt in range(1, retries + 2):  # retries + 1 attempts
        try:
            return make_request()
        except _TRANSIENT_ERRORS as error:
            last_error = error
            if attempt > retries:
                break
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise RuntimeError(f"{label}: transient API errors after {retries + 1} attempts: {last_error}")


def call_llm(system_prompt: str, user_prompt: str, max_output_tokens: int = 2000) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_prompt,
        input=user_prompt,
        max_output_tokens=max_output_tokens,
    )
    return response.output_text.strip()

def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No complete JSON object found in LLM output:\n{text}")
    possible_json = cleaned[start: end + 1]
    return json.loads(possible_json)


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int = 6000,
    retries: int = 3,
) -> Dict[str, Any]:

    last_raw = ""
    strict_system_prompt = (
        system_prompt
        + """
Important JSON rules:
- Return only one valid JSON object.
- Do not use markdown fences.
- Do not include text before or after the JSON.
- Keep string values concise.
- Do not write extremely long reasoning.
- Make sure every opened bracket and quote is closed.
"""
    )
    current_prompt = user_prompt
    for attempt in range(1, retries + 1):
        raw = call_llm(
            strict_system_prompt,
            current_prompt,
            max_output_tokens=max_output_tokens,
        )
        last_raw = raw
        try:
            return extract_json(raw)
        except Exception as error:
            current_prompt = f"""
Your previous response was invalid JSON.
Error:
{str(error)}
Return the same content again, but as one complete valid JSON object.
Do not include markdown.
Do not include explanations outside JSON.
Keep all string fields concise enough that the response is not cut off.
Previous invalid response:
{raw}
"""
    raise ValueError(f"Failed to get valid JSON after {retries} attempts.\nLast output:\n{last_raw}")


def call_llm_model(
    system_prompt: str,
    user_prompt: str,
    model: Type[ModelT],
    max_output_tokens: int = 6000,
    retries: int = MAX_RETRIES,
    effort: str = "medium",
    verbosity: str = "low",
) -> ModelT:
    """Structured Pydantic output via OpenAI's parse endpoint.

    `effort` controls reasoning depth. Solve/review/refine/judge stages should
    use a moderate effort so the debate actually reasons; cheap stages such as
    the Stage-0 role self-assessment can pass effort="minimal".

    Robustness:
    - transient API errors (rate limit / timeout / connection) are retried with
      exponential backoff;
    - if the model rejects the reasoning/verbosity controls (non-reasoning models),
      they are dropped automatically and the call is retried without them.
    """

    global _MODEL_SUPPORTS_REASONING

    if not hasattr(client.responses, "parse"):
        raise RuntimeError(
            "The installed OpenAI SDK does not support responses.parse. "
            "Install openai>=1.90.0 to use Pydantic structured outputs."
        )

    token_budget = max_output_tokens
    last_error = ""

    for attempt in range(1, retries + 2):
        request_kwargs: dict[str, Any] = dict(
            model=OPENAI_MODEL,
            instructions=system_prompt,
            input=user_prompt,
            max_output_tokens=token_budget,
            text_format=model,
        )
        if _MODEL_SUPPORTS_REASONING:
            request_kwargs["reasoning"] = {"effort": effort}
            request_kwargs["text"] = {"verbosity": verbosity}

        try:
            response = _with_backoff(
                lambda: client.responses.parse(**request_kwargs),
                retries=retries,
                label=f"structured output for {model.__name__}",
            )
        except LengthFinishReasonError as error:
            last_error = str(error)
            token_budget = min(token_budget * 2, 12000)
            continue
        except BadRequestError as error:
            # Most likely the model does not accept reasoning/verbosity controls.
            if _MODEL_SUPPORTS_REASONING:
                _MODEL_SUPPORTS_REASONING = False
                last_error = f"dropped reasoning/verbosity controls: {error}"
                continue
            raise RuntimeError(
                f"Structured output request failed for {model.__name__}: {error}"
            ) from error
        except Exception as error:
            raise RuntimeError(
                f"Structured output request failed for {model.__name__}: {error}"
            ) from error

        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            if isinstance(parsed, model):
                return parsed
            return model.model_validate(parsed)

        raw_text = getattr(response, "output_text", "")
        if raw_text:
            try:
                return model.model_validate_json(raw_text)
            except ValidationError as error:
                last_error = str(error)
                token_budget = min(token_budget * 2, 12000)
                continue

        last_error = "empty structured output"

    raise ValueError(
        f"Failed to get structured Pydantic output as {model.__name__} "
        f"after {retries} attempts. Last error: {last_error}"
    )
