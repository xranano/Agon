import json
import os
import re
from typing import Any, Dict, Type, TypeVar
from dotenv import load_dotenv
from openai import LengthFinishReasonError, OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your local .env file.")
client = OpenAI(api_key=OPENAI_API_KEY)
ModelT = TypeVar("ModelT", bound=BaseModel)


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
    retries: int = 3,
) -> ModelT:
    if not hasattr(client.responses, "parse"):
        raise RuntimeError(
            "The installed OpenAI SDK does not support responses.parse. "
            "Install openai>=1.90.0 to use Pydantic structured outputs."
        )

    token_budget = max_output_tokens
    last_error = ""

    for attempt in range(1, retries + 1):
        try:
            response = client.responses.parse(
                model=OPENAI_MODEL,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=token_budget,
                text_format=model,
                reasoning={"effort": "minimal"},
                text={"verbosity": "low"},
            )
        except LengthFinishReasonError as error:
            last_error = str(error)
            token_budget = min(token_budget * 2, 12000)
            continue
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
