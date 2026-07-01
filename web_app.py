"""Local web server for the Agon debate interface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, ROOT_DIR


WEBSITE_DIR = ROOT_DIR / "website"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True)
class DebateAgent:
    id: str
    name: str
    role_name: str
    color: str
    framework: str
    system_prompt: str


AGENTS = [
    DebateAgent(
        id="kant",
        name="Immanuel Kant",
        role_name="Opening Statement",
        color="#141414",
        framework="Deontology",
        system_prompt=(
            "You are an AI reasoning agent role-playing Immanuel Kant inside a formal philosophical "
            "debate chamber called Agon. Argue from deontology, universal law, duty, autonomy, and "
            "the treatment of persons as ends. Do not claim to be the historical person."
        ),
    ),
    DebateAgent(
        id="mill",
        name="John Stuart Mill",
        role_name="Opening Statement",
        color="#dc2626",
        framework="Utilitarianism",
        system_prompt=(
            "You are an AI reasoning agent role-playing John Stuart Mill inside a formal philosophical "
            "debate chamber called Agon. Argue from utility, liberty, welfare, consequences, and higher "
            "pleasures. Do not claim to be the historical person."
        ),
    ),
    DebateAgent(
        id="nietzsche",
        name="Friedrich Nietzsche",
        role_name="Opening Statement",
        color="#7c5cfc",
        framework="Genealogical critique",
        system_prompt=(
            "You are an AI reasoning agent role-playing Friedrich Nietzsche inside a formal philosophical "
            "debate chamber called Agon. Argue forcefully, expose hidden values, resist herd morality, "
            "and challenge weak assumptions. Do not claim to be the historical person."
        ),
    ),
    DebateAgent(
        id="camus",
        name="Albert Camus",
        role_name="Opening Statement",
        color="#a9784f",
        framework="Absurdism",
        system_prompt=(
            "You are an AI reasoning agent role-playing Albert Camus inside a formal philosophical "
            "debate chamber called Agon. Argue from lucidity, revolt, limits, human solidarity, and "
            "the refusal of false consolation. Do not claim to be the historical person."
        ),
    ),
]

JUDGE = DebateAgent(
    id="socrates",
    name="Socrates",
    role_name="Verdict",
    color="#9c2c53",
    framework="Elenctic judgment",
    system_prompt=(
        "You are an AI reasoning agent role-playing Socrates as neutral arbiter in a formal "
        "philosophical debate chamber called Agon. Question premises, identify contradictions, "
        "weigh the arguments, and render a concise judgment. Do not claim to be the historical person."
    ),
)


def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env before opening proceedings.")
    return OpenAI(api_key=OPENAI_API_KEY)


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(str(value))
    return "\n".join(chunks).strip()


def _complete(client: OpenAI, system_prompt: str, user_prompt: str) -> str:
    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = _response_text(response)
        if text:
            return text
    except AttributeError:
        pass

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _compile_transcript(turns: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{turn['speaker']} ({turn['role']}): {turn['text']}" for turn in turns)


def _agent_prompt(agent: DebateAgent, role_name: str, question: str, transcript: str, phase: str) -> str:
    if phase == "rebuttal":
        instruction = (
            "Directly engage specific claims already made. Name the weak point before restating "
            "your own position."
        )
    else:
        instruction = "State your position clearly and argue from your framework's first principles."

    return "\n".join(
        [
            f"Question before the tribunal: {question}",
            "",
            "Transcript so far:",
            transcript or "(You are the first to speak.)",
            "",
            f"Deliver {agent.name}'s {role_name}. {instruction}",
            "Write 80-120 words, first person, as spoken argument only.",
            "No markdown, no stage directions, no name label, no surrounding quotation marks.",
        ]
    )


def _judge_prompt(question: str, transcript: str) -> str:
    return "\n".join(
        [
            f"Question before the tribunal: {question}",
            "",
            "Full transcript:",
            transcript,
            "",
            "Examine the strongest and weakest points in 100-150 words, first person as Socrates.",
            "Use brief questioning before ruling. No markdown, no stage directions.",
            'End with one final line starting exactly with "VERDICT:" followed by one sentence under 18 words.',
        ]
    )


def run_debate(question: str) -> list[dict[str, str]]:
    client = _client()
    turns: list[dict[str, str]] = []

    for agent in AGENTS:
        text = _complete(
            client,
            agent.system_prompt,
            _agent_prompt(agent, agent.role_name, question, _compile_transcript(turns), "opening"),
        )
        turns.append(
            {
                "speaker": agent.name,
                "role": agent.role_name,
                "color": agent.color,
                "text": text or "[Silence.]",
            }
        )

    for agent in AGENTS:
        text = _complete(
            client,
            agent.system_prompt,
            _agent_prompt(agent, "Rebuttal", question, _compile_transcript(turns), "rebuttal"),
        )
        turns.append(
            {
                "speaker": agent.name,
                "role": "Rebuttal",
                "color": agent.color,
                "text": text or "[Silence.]",
            }
        )

    text = _complete(client, JUDGE.system_prompt, _judge_prompt(question, _compile_transcript(turns)))
    turns.append(
        {
            "speaker": JUDGE.name,
            "role": JUDGE.role_name,
            "color": JUDGE.color,
            "text": text or "[Silence.]",
        }
    )
    return turns


class AgonHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEBSITE_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path in {"/", ""}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/debate":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            if not question:
                raise ValueError("Question is required.")
            turns = run_debate(question)
            self._send_json({"turns": turns})
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), AgonHandler)
    print(f"Agon running at http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
