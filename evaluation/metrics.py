"""Evaluation metrics and lightweight answer grading."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from config import DATA_DIR, RESULTS_DIR


WORD_RE = re.compile(r"[a-z0-9]+")


ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kant": (
        "kant",
        "deontology",
        "duty",
        "universal",
        "autonomy",
        "dignity",
        "consent",
        "merely as a means",
    ),
    "mill": (
        "mill",
        "utilitarian",
        "utility",
        "welfare",
        "harm",
        "consequences",
        "liberty",
        "happiness",
    ),
    "nietzsche": (
        "nietzsche",
        "values",
        "herd",
        "power",
        "resentment",
        "authenticity",
        "self-overcoming",
        "critique",
    ),
    "camus": (
        "camus",
        "limits",
        "lucid",
        "lucidity",
        "revolt",
        "solidarity",
        "concrete",
        "absurd",
    ),
}


def load_problems(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the evaluation problem set."""

    problems_path = path or DATA_DIR / "problems.json"
    with problems_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return list(data.get("problems", []))
    return data


def normalize_text(value: Any) -> str:
    """Normalize free-form text for rubric checks."""

    return " ".join(WORD_RE.findall(str(value).lower()))


def _token_set(value: str) -> set[str]:
    return set(WORD_RE.findall(value.lower()))


def _concept_hit(concept: str, normalized_answer: str, answer_tokens: set[str]) -> bool:
    normalized_concept = normalize_text(concept)
    if normalized_concept in normalized_answer:
        return True
    concept_tokens = _token_set(concept)
    if not concept_tokens:
        return False
    hits = len(concept_tokens & answer_tokens)
    return hits == len(concept_tokens) or hits / len(concept_tokens) >= 0.67


def role_coverage(answer: Any) -> dict[str, bool]:
    """Detect whether an answer engages each philosopher role."""

    normalized = normalize_text(answer)
    tokens = _token_set(str(answer))
    coverage: dict[str, bool] = {}
    for role, keywords in ROLE_KEYWORDS.items():
        coverage[role] = any(_concept_hit(keyword, normalized, tokens) for keyword in keywords)
    return coverage


def grade_answer(problem: dict[str, Any], answer: Any) -> dict[str, Any]:
    """Grade one philosopher-debate answer.

    The score combines expected verdict, required rubric concepts, and broader
    overlap with the expected answer and grading notes. This stays simple and
    auditable while matching the philosopher-inspired debate format.
    """

    answer_text = str(answer or "")
    normalized = normalize_text(answer_text)
    problem_id = str(problem["id"])
    answer_tokens = _token_set(answer_text)
    required_concepts = [str(item) for item in problem.get("required_concepts", [])]
    concept_hits = [
        concept
        for concept in required_concepts
        if _concept_hit(concept, normalized, answer_tokens)
    ]
    expected_verdict = normalize_text(problem.get("expected_verdict", ""))
    verdict_hit = not expected_verdict or expected_verdict in normalized

    expected_tokens = _token_set(problem["expected_answer"])
    notes_tokens = _token_set(problem["grading_notes"])
    rubric_tokens = expected_tokens | {t for t in notes_tokens if len(t) > 4}
    overlap = len(answer_tokens & rubric_tokens) / max(1, len(rubric_tokens))
    concept_score = len(concept_hits) / max(1, len(required_concepts))
    verdict_score = 1.0 if verdict_hit else 0.0
    score = round((concept_score * 0.7) + (verdict_score * 0.2) + (overlap * 0.1), 3)
    score = min(1.0, score)

    return {
        "problem_id": problem_id,
        "correct": score >= 0.7,
        "score": score,
        "concept_hits": concept_hits,
        "verdict_hit": verdict_hit,
        "role_coverage": role_coverage(answer_text),
    }


def evaluate_answer_rows(rows: list[dict[str, Any]], problems: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach grading data to rows containing problem_id, system, and answer."""

    by_id = {problem["id"]: problem for problem in problems}
    graded: list[dict[str, Any]] = []
    for row in rows:
        problem = by_id[row["problem_id"]]
        grade = grade_answer(problem, row.get("answer", ""))
        graded.append(
            {
                **row,
                "expected_verdict": problem.get("expected_verdict", ""),
                "required_concepts": problem.get("required_concepts", []),
                **grade,
            }
        )
    return graded


def summarize_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute overall, category, and comparative metrics."""

    by_system: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)

    systems: dict[str, dict[str, Any]] = {}
    for system, items in sorted(by_system.items()):
        correct_count = sum(1 for item in items if item["correct"])
        systems[system] = {
            "n": len(items),
            "accuracy": correct_count / max(1, len(items)),
            "mean_score": mean(item["score"] for item in items) if items else 0.0,
            "correct": correct_count,
        }

    categories: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for system, items in sorted(by_system.items()):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            grouped[item.get("category", "unknown")].append(item)
        for category, cat_items in sorted(grouped.items()):
            categories[category][system] = {
                "accuracy": sum(1 for item in cat_items if item["correct"]) / len(cat_items),
                "mean_score": mean(item["score"] for item in cat_items),
            }

    by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_problem[row["problem_id"]].append(row)

    consensus_flags = []
    improvement_flags = []
    judge_flags = []
    role_totals: dict[str, list[bool]] = defaultdict(list)
    for items in by_problem.values():
        answer_counts = Counter(normalize_text(item.get("answer", "")) for item in items)
        consensus_flags.append(answer_counts.most_common(1)[0][1] >= 2)

        single = next((item for item in items if item["system"] == "single_agent_baseline"), None)
        debate = next((item for item in items if item["system"] == "full_debate"), None)
        if single and debate:
            improvement_flags.append((not single["correct"]) and debate["correct"])
            judge_flags.append(debate["correct"])

    for row in rows:
        if (
            row["system"] == "full_debate"
            and row.get("category") == "philosophical_ethical_reasoning"
        ):
            for role, covered in row.get("role_coverage", {}).items():
                role_totals[role].append(bool(covered))

    return {
        "systems": systems,
        "categories": categories,
        "improvement_rate": sum(improvement_flags) / max(1, len(improvement_flags)),
        "consensus_rate": sum(consensus_flags) / max(1, len(consensus_flags)),
        "judge_accuracy": sum(judge_flags) / max(1, len(judge_flags)),
        "ethical_full_debate_role_coverage": {
            role: sum(values) / max(1, len(values))
            for role, values in sorted(role_totals.items())
        },
        "ethical_role_mapping": {
            "solver_1": "Kant - deontological reasoning",
            "solver_2": "Mill - utilitarian reasoning",
            "solver_3": "Nietzsche - critique of values and assumptions",
            "judge": "Camus - clarity, limits, and human consequences",
        },
    }


def save_evaluation(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Write evaluation JSON and CSV artifacts."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "evaluation_rows.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    csv_lines = [
        "problem_id,category,difficulty,system,expected_verdict,correct,score,"
        "kant_covered,mill_covered,nietzsche_covered,camus_covered,answer"
    ]
    for row in rows:
        answer = str(row.get("answer", "")).replace('"', '""')
        coverage = row.get("role_coverage", {})
        csv_lines.append(
            f'{row["problem_id"]},{row.get("category","")},{row.get("difficulty","")},'
            f'{row["system"]},{row.get("expected_verdict","")},{row["correct"]},{row["score"]},'
            f'{coverage.get("kant", False)},{coverage.get("mill", False)},'
            f'{coverage.get("nietzsche", False)},{coverage.get("camus", False)},"{answer}"'
        )
    (RESULTS_DIR / "evaluation_rows.csv").write_text("\n".join(csv_lines), encoding="utf-8")


def main() -> None:
    rows_path = RESULTS_DIR / "baseline_comparison.json"
    if not rows_path.exists():
        raise SystemExit("Run `python -m evaluation.baseline` before metrics.")
    problems = load_problems()
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    graded = evaluate_answer_rows(rows, problems)
    summary = summarize_results(graded)
    save_evaluation(graded, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
