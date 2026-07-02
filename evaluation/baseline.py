"""Baseline comparison, scored by tradition-match against `expected_strongest_tradition`
rather than free-text grading. Every system is derived from a single real
pipeline run (``results/debate_runs.json``), so the comparison is apples-to-
apples (same model, same problems, same prompts):

- ``single_agent_baseline`` : one solver's tradition (Stage 1, pre-debate).
- ``majority_vote_baseline``: majority tradition over the three Stage-1 answers
  by near-duplicate text clustering, falling back to the highest self-reported
  Stage-1 confidence when no majority forms -- the expected common case, given
  persona distinctness is a design goal. `fallback_rate` reports how often.
- ``full_debate``          : the judge's winning tradition after peer review + refinement.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from config import RESULTS_DIR
from evaluation.metrics import (
    load_debate_runs,
    load_problems,
    ordered_solver_roles,
    solver_tradition,
    text_similarity,
    winner_tradition,
)

VOTE_SIMILARITY_THRESHOLD = 0.6


def single_llm_tradition(run: dict[str, Any]) -> str:
    """Tradition of the first Stage-1 solver (pre-debate, single-agent baseline)."""

    roles = ordered_solver_roles(run)
    return solver_tradition(run, roles[0]) if roles else ""


def _cluster_indices(texts: list[str], threshold: float) -> list[list[int]]:
    """Union-find clustering of texts by pairwise near-duplicate similarity."""

    parent = list(range(len(texts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if text_similarity(texts[i], texts[j]) >= threshold:
                root_i, root_j = find(i), find(j)
                if root_i != root_j:
                    parent[root_i] = root_j

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(len(texts)):
        clusters[find(i)].append(i)
    return list(clusters.values())


def simple_voting_tradition(run: dict[str, Any]) -> tuple[str, bool]:
    """Majority position among the 3 Stage-1 answers; falls back to highest
    self-reported confidence if no majority cluster forms. Returns
    (chosen_tradition, used_fallback)."""

    roles = ordered_solver_roles(run)
    if not roles:
        return "", True

    solutions = run.get("initial_solutions", {})
    answers = [str(solutions.get(role, {}).get("answer", "")) for role in roles]

    def confidence(role: str) -> float:
        return float(solutions.get(role, {}).get("confidence", 0.0))

    clusters = _cluster_indices(answers, VOTE_SIMILARITY_THRESHOLD)
    largest = max(clusters, key=len)
    if len(largest) >= 2:
        best_index = max(largest, key=lambda i: confidence(roles[i]))
        return solver_tradition(run, roles[best_index]), False

    best_index = max(range(len(roles)), key=lambda i: confidence(roles[i]))
    return solver_tradition(run, roles[best_index]), True


def build_baseline_rows(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Create one comparison row per problem from real debate runs."""

    rows = []
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue

        expected = str(problem.get("expected_strongest_tradition", "")).strip().lower()
        single_tradition = single_llm_tradition(run)
        majority_tradition, used_fallback = simple_voting_tradition(run)
        full_debate_tradition = winner_tradition(run)

        rows.append(
            {
                "problem_id": problem["id"],
                "category": problem.get("category", "unknown"),
                "difficulty": problem.get("difficulty", "unknown"),
                "expected_strongest_tradition": expected,
                "single_agent_tradition": single_tradition,
                "single_agent_correct": bool(expected) and single_tradition == expected,
                "majority_vote_tradition": majority_tradition,
                "majority_vote_correct": bool(expected) and majority_tradition == expected,
                "majority_vote_used_fallback": used_fallback,
                "full_debate_tradition": full_debate_tradition,
                "full_debate_correct": bool(expected) and full_debate_tradition == expected,
            }
        )
    return rows


def baseline_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)

    def _system(correct_key: str) -> dict[str, Any]:
        correct = sum(1 for row in rows if row[correct_key])
        return {"n": n, "correct": correct, "accuracy": correct / n if n else 0.0}

    fallback_count = sum(1 for row in rows if row["majority_vote_used_fallback"])
    return {
        "systems": {
            "single_agent_baseline": _system("single_agent_correct"),
            "majority_vote_baseline": _system("majority_vote_correct"),
            "full_debate": _system("full_debate_correct"),
        },
        "fallback_rate": fallback_count / n if n else 0.0,
    }


def save_rows(rows: list[dict[str, Any]], path: Path | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = path or RESULTS_DIR / "baseline_comparison.json"
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def main() -> None:
    problems = load_problems()
    runs = load_debate_runs()
    rows = build_baseline_rows(problems, runs)
    output_path = save_rows(rows)
    print(f"Wrote {len(rows)} comparison rows (from real debate runs) to {output_path}")
    print(json.dumps(baseline_summary(rows), indent=2))


if __name__ == "__main__":
    main()
