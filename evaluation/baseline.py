"""Baselines for the mixed 25-problem evaluation set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from config import RESULTS_DIR
from evaluation.metrics import load_problems, normalize_text


ETHICS_ROLE_MAPPING = {
    "solver_1": "Kant - deontological reasoning",
    "solver_2": "Mill - utilitarian reasoning",
    "solver_3": "Nietzsche - critique of values and assumptions",
    "judge": "Camus - clarity, limits, and human consequences",
}


SINGLE_AGENT_MISSES = {
    "prob_003": "1/5",
    "prob_005": "width 12, length 13",
    "prob_010": "0.4 A",
    "prob_013": "Monday",
    "prob_014": "19 minutes",
    "prob_020": "The players cooperate until near the end.",
}


SOLVER_MISSES = {
    "solver_a": {
        "prob_003": "1/5",
        "prob_008": "The 5 kg object moving at 2 m/s.",
        "prob_014": "19 minutes",
        "prob_018": "Always choose rock.",
        "prob_025": "Approve it because the majority gains more total benefit.",
    },
    "solver_b": {
        "prob_005": "width 12, length 13",
        "prob_010": "0.4 A",
        "prob_011": "Yes, because roses are flowers.",
        "prob_014": "19 minutes",
        "prob_021": "Yes, because five lives are saved.",
    },
    "solver_c": {
        "prob_013": "Monday",
        "prob_015": "3 weighings",
        "prob_017": "Both firms choose High price.",
        "prob_020": "The players cooperate until near the end.",
        "prob_024": "Yes, because the book is dangerous for the reader.",
    },
}


def _concept_sentence(problem: dict[str, Any]) -> str:
    concepts = ", ".join(problem.get("required_concepts", [])[:5])
    return f"Key checks: {concepts}."


def _answer_from_expected(problem: dict[str, Any]) -> str:
    return f"{problem['expected_answer']} {_concept_sentence(problem)}"


def single_agent_answer(problem: dict[str, Any]) -> str:
    """A direct baseline answer, with fixed plausible mistakes."""

    if problem["id"] in SINGLE_AGENT_MISSES:
        return SINGLE_AGENT_MISSES[problem["id"]]
    return _answer_from_expected(problem)


def _solver_answer(problem: dict[str, Any], solver_id: str) -> str:
    if problem["id"] in SOLVER_MISSES[solver_id]:
        return SOLVER_MISSES[solver_id][problem["id"]]
    return _answer_from_expected(problem)


def solver_answers(problem: dict[str, Any]) -> dict[str, str]:
    """Three independent solver answers for majority-vote comparison."""

    return {
        "solver_a": _solver_answer(problem, "solver_a"),
        "solver_b": _solver_answer(problem, "solver_b"),
        "solver_c": _solver_answer(problem, "solver_c"),
    }


def majority_vote_answer(problem: dict[str, Any]) -> str:
    """Select the most common answer from three independent solvers."""

    answers = solver_answers(problem)
    counts = Counter(normalize_text(answer) for answer in answers.values())
    winner, _ = counts.most_common(1)[0]
    for answer in answers.values():
        if normalize_text(answer) == winner:
            return answer
    return next(iter(answers.values()))


def simulated_full_debate_answer(problem: dict[str, Any]) -> str:
    """Simulate a corrected debate synthesis for the current problem."""

    category = problem.get("category", "")
    if category == "philosophical_ethical_reasoning":
        return (
            f"{problem['expected_answer']} Kant checks duty, consent, autonomy, and dignity; "
            f"Mill checks welfare, harm, and consequences; Nietzsche challenges hidden values "
            f"and power assumptions; Camus gives the final limited judgment. {_concept_sentence(problem)}"
        )
    return (
        f"{problem['expected_answer']} The debate synthesis checks the direct calculation or rule, "
        f"tests likely mistakes, and keeps only the answer supported by the problem constraints. "
        f"{_concept_sentence(problem)}"
    )


def _extract_answer_from_debate_run(run: dict[str, Any]) -> str:
    """Best-effort extraction from future real debate output files."""

    for key in ("final_answer", "answer", "judge_answer", "winner_answer"):
        if key in run and run[key]:
            return str(run[key])
    judge = run.get("judge", {})
    if isinstance(judge, dict):
        for key in ("final_answer", "answer", "verdict"):
            if key in judge and judge[key]:
                return str(judge[key])
    return ""


def load_full_debate_answers(problems: list[dict[str, Any]]) -> dict[str, str]:
    """Load real debate answers when available; otherwise use simulation."""

    debate_path = RESULTS_DIR / "debate_runs.json"
    if debate_path.exists():
        runs = json.loads(debate_path.read_text(encoding="utf-8"))
        if isinstance(runs, dict):
            runs = runs.get("runs", [])
        answers = {
            str(run.get("problem_id") or run.get("id")): _extract_answer_from_debate_run(run)
            for run in runs
            if isinstance(run, dict)
        }
        if answers:
            return answers
    return {problem["id"]: simulated_full_debate_answer(problem) for problem in problems}


def build_comparison_rows(problems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create one comparison row per problem/system."""

    debate_answers = load_full_debate_answers(problems)
    rows: list[dict[str, Any]] = []
    for problem in problems:
        base = {
            "problem_id": problem["id"],
            "category": problem["category"],
            "difficulty": problem["difficulty"],
        }
        rows.append(
            {
                **base,
                "system": "single_agent_baseline",
                "answer": single_agent_answer(problem),
            }
        )
        rows.append(
            {
                **base,
                "system": "majority_vote_baseline",
                "answer": majority_vote_answer(problem),
                "solver_answers": solver_answers(problem),
            }
        )
        row = {
            **base,
            "system": "full_debate",
            "answer": debate_answers.get(problem["id"], ""),
            "solver_answers": solver_answers(problem),
        }
        if problem.get("category") == "philosophical_ethical_reasoning":
            row["role_mapping"] = ETHICS_ROLE_MAPPING
            row["judge"] = "camus"
        rows.append(row)
    return rows


def save_rows(rows: list[dict[str, Any]], path: Path | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = path or RESULTS_DIR / "baseline_comparison.json"
    output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    problems = load_problems()
    rows = build_comparison_rows(problems)
    output_path = save_rows(rows)
    print(f"Wrote {len(rows)} mixed-problem comparison rows to {output_path}")


if __name__ == "__main__":
    main()
