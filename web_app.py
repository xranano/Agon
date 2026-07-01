"""Local web server for the Agon debate interface."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from config import DATA_DIR, ROOT_DIR
from main import run_single_problem


WEBSITE_DIR = ROOT_DIR / "website"
HISTORY_PATH = DATA_DIR / "history.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = int(os.getenv("AGON_PORT", "8000"))


AGENT_META = {
    "agent_1": {"name": "Kant", "color": "#141414"},
    "agent_2": {"name": "Nietzsche", "color": "#7c5cfc"},
    "agent_3": {"name": "Aristotle", "color": "#a9784f"},
    "agent_4": {"name": "Plato", "color": "#dc2626"},
    "agent_5": {"name": "Camus", "color": "#9c2c53"},
}


def _agent_meta(agent_id: str) -> dict[str, str]:
    return AGENT_META.get(agent_id, {"name": agent_id, "color": "#7c5cfc"})


def _problem_from_question(question: str) -> dict[str, str]:
    return {
        "id": "frontend_case",
        "category": "frontend",
        "difficulty": "unspecified",
        "question": question,
        "expected_answer": "",
        "grading_notes": "",
    }


def _assignment_text(run: dict[str, Any]) -> str:
    roles = run["assigned_roles"]
    judge = _agent_meta(roles["judge"])["name"]
    solver_names = [
        f"{role}: {_agent_meta(agent_id)['name']}"
        for role, agent_id in roles["solver_roles"].items()
    ]
    selector_note = f" Reasoning: {roles['selector_reasoning']}" if roles.get("selector_reasoning") else ""
    return (
        f"Mode: {roles['selection_mode']}. Judge: {judge}. "
        f"Solvers: {'; '.join(solver_names)}. Rule: {roles['assignment_rule']}."
        f"{selector_note}"
    )


def _review_summary(review: dict[str, Any]) -> str:
    weaknesses = "; ".join(review.get("weaknesses", [])[:2]) or "No major weakness recorded."
    changes = "; ".join(review.get("suggested_changes", [])[:2]) or "No specific change requested."
    return (
        f"Assessment: {review.get('overall_assessment', 'unknown')}. "
        f"Weaknesses: {weaknesses}. Suggested changes: {changes}"
    )


def _brief_text(value: Any, max_chars: int = 900) -> str:
    lines = [" ".join(line.split()) for line in str(value or "").splitlines()]
    text = "\n".join(line for line in lines if line)
    if not text:
        return ""
    text = re.sub(r"\s+(\d+\.)", r"\n\1", text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rsplit(" ", 1)[0] + "."


def _confidence(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "n/a"


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    with HISTORY_PATH.open("r", encoding="utf-8") as file:
        history = json.load(file)
    if not isinstance(history, list):
        raise ValueError("history.json must contain a list.")
    return history


def save_history(history: list[dict[str, Any]]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)


def save_history_entry(question: str, verdict: str) -> dict[str, Any]:
    history = load_history()
    case_no = max((int(entry.get("case_no", 0)) for entry in history), default=0) + 1
    entry = {
        "case_no": case_no,
        "question": question,
        "verdict": verdict,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    history.append(entry)
    save_history(history)
    return entry


def run_debate(
    question: str,
    selection_mode: str = "auto",
    selected_judge: str | None = None,
    selected_solvers: list[str] | None = None,
) -> dict[str, Any]:
    run = run_single_problem(
        _problem_from_question(question),
        selection_mode=selection_mode,
        selected_judge=selected_judge,
        selected_solvers=selected_solvers,
    )
    turns: list[dict[str, str]] = [
        {
            "speaker": "Agon",
            "role": "Role Assignment",
            "color": "#7c5cfc",
            "text": _assignment_text(run),
        }
    ]

    for solver_role, solution in run["initial_solutions"].items():
        meta = _agent_meta(solution["agent_id"])
        turns.append(
            {
                "speaker": meta["name"],
                "role": f"{solver_role} Initial Solution",
                "color": meta["color"],
                "text": (
                    f"Reasoning:\n{_brief_text(solution['solution'])}\n\n"
                    f"Answer:\n{_brief_text(solution['answer'], 300)}\n\n"
                    f"Confidence: {_confidence(solution.get('confidence'))}"
                ),
            }
        )

    for target_role, reviews in run["peer_reviews"].items():
        for reviewer_role, review in reviews.items():
            reviewer_agent_id = run["assigned_roles"]["solver_roles"][reviewer_role]
            meta = _agent_meta(reviewer_agent_id)
            turns.append(
                {
                    "speaker": meta["name"],
                    "role": f"Review of {target_role}",
                    "color": meta["color"],
                    "text": _review_summary(review),
                }
            )

    for solver_role, refinement in run["refinements"].items():
        meta = _agent_meta(refinement["agent_id"])
        turns.append(
            {
                "speaker": meta["name"],
                "role": f"{solver_role} Refinement",
                "color": meta["color"],
                "text": (
                    f"Revision:\n{_brief_text(refinement['refined_solution'])}\n\n"
                    f"Refined answer:\n{_brief_text(refinement['refined_answer'], 300)}\n\n"
                    f"Confidence: {_confidence(refinement.get('confidence'))}"
                ),
            }
        )

    judge = run["judge_decision"]
    judge_meta = _agent_meta(judge["judge_agent_id"])
    turns.append(
        {
            "speaker": judge_meta["name"],
            "role": "Verdict",
            "color": judge_meta["color"],
            "text": (
                f"Reasoning:\n{_brief_text(judge['reasoning'], 600)}\n\n"
                f"Winner: {judge['winner']}\n\n"
                f"Verdict:\n{_brief_text(judge['final_answer'], 400)}"
            ),
        }
    )
    return {"turns": turns, "run": run}


class AgonHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEBSITE_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/history":
            self._send_json({"history": load_history()})
            return
        if path in {"/", ""}:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/history":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                question = str(payload.get("question", "")).strip()
                verdict = str(payload.get("verdict", "")).strip()
                if not question:
                    raise ValueError("Question is required.")
                if not verdict:
                    raise ValueError("Verdict is required.")
                self._send_json({"entry": save_history_entry(question, verdict)})
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path != "/api/debate":
            self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            selection_mode = str(payload.get("selection_mode", "auto")).strip() or "auto"
            selected_judge = payload.get("selected_judge")
            selected_solvers = payload.get("selected_solvers")
            if not question:
                raise ValueError("Question is required.")
            if selection_mode not in {"auto", "selector"}:
                raise ValueError("selection_mode must be 'auto' or 'selector'.")
            if selected_judge is not None:
                selected_judge = str(selected_judge)
            if selected_solvers is not None:
                if not isinstance(selected_solvers, list):
                    raise ValueError("selected_solvers must be a list.")
                selected_solvers = [str(agent_id) for agent_id in selected_solvers]
            result = run_debate(
                question,
                selection_mode=selection_mode,
                selected_judge=selected_judge,
                selected_solvers=selected_solvers,
            )
            self._send_json(result)
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
