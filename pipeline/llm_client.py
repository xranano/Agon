import json
import os
import re
from typing import Any, Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your local .env file.")
client = OpenAI(api_key=OPENAI_API_KEY)
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
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM output:\n{text}")

    return json.loads(match.group(0))


def call_llm_json(system_prompt: str, user_prompt: str, max_output_tokens: int = 2000) -> Dict[str, Any]:
    raw = call_llm(system_prompt, user_prompt, max_output_tokens=max_output_tokens)
    try:
        return extract_json(raw)
    except Exception:
        repair_prompt = f"""
Your previous response was not valid JSON.

Return only one valid JSON object.
Do not include markdown.
Do not include explanations outside JSON.

Previous response:
{raw}
"""
        repaired = call_llm(system_prompt, repair_prompt, max_output_tokens=max_output_tokens)
        return extract_json(repaired)