"""Evaluation metrics for the project-agon philosophy debate system, computed
from real debate runs (``results/debate_runs.json``).

The new dataset schema carries ``expected_strongest_tradition`` per problem
(not a free-text ``expected_answer``), so Verdict Accuracy is now a
deterministic tradition match -- no LLM grading needed, and much more
defensible than comparing free text. The metrics that still need a
persona-free LLM grader are Improvement Rate (order-bias controlled Stage 1
vs Stage 3 comparison, scoped to the judge's winning solver) and Persona
Distinctness (semantic convergence check). Fidelity rubric scoring lives in
``evaluation.fidelity_rubrics``; the Judge-Bias Analysis lives in
``evaluation.judge_bias``; baseline scoring lives in ``evaluation.baseline``.
"""

from __future__ import annotations

import difflib
import json
import random
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from config import DATA_DIR, RESULTS_DIR
from evaluation import llm_cache
from pipeline.agent_registry import get_agent

WORD_RE = re.compile(r"[a-z0-9]+")


# --------------------------------------------------------------------------- #
# Loading + text helpers (schema-independent, shared with evaluation.baseline)
# --------------------------------------------------------------------------- #
def load_problems(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the evaluation problem set (supports {"problems": [...]} or a bare list)."""

    problems_path = path or DATA_DIR / "problems.json"
    with problems_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return list(data.get("problems", []))
    return data


def normalize_text(value: Any) -> str:
    """Normalize free-form text to a canonical token string."""

    return " ".join(WORD_RE.findall(str(value).lower()))


def load_debate_runs(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load real debate runs from ``results/debate_runs.json``, indexed by problem id."""

    runs_path = path or RESULTS_DIR / "debate_runs.json"
    if not runs_path.exists():
        raise SystemExit(
            f"{runs_path} not found. Run `python main.py` to generate real debate "
            "runs before evaluating."
        )
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    if isinstance(runs, dict):
        runs = runs.get("runs", [])
    indexed: dict[str, dict[str, Any]] = {}
    for run in runs:
        if isinstance(run, dict):
            problem_id = str(run.get("problem_id") or run.get("id") or "")
            if problem_id:
                indexed[problem_id] = run
    return indexed


def ordered_solver_roles(run: dict[str, Any]) -> list[str]:
    return sorted(run.get("assigned_roles", {}).get("solver_roles", {}).keys())


def initial_answers(run: dict[str, Any]) -> list[str]:
    solutions = run.get("initial_solutions", {})
    return [str(solutions.get(role, {}).get("answer", "")) for role in ordered_solver_roles(run)]


def refined_answers(run: dict[str, Any]) -> list[str]:
    refinements = run.get("refinements", {})
    return [
        str(refinements.get(role, {}).get("refined_answer", ""))
        for role in ordered_solver_roles(run)
    ]


def final_debate_answer(run: dict[str, Any]) -> str:
    return str(run.get("judge_decision", {}).get("final_answer", run.get("final_answer", "")))


def majority_answer(answers: list[str]) -> str:
    if not answers:
        return ""
    counts = Counter(normalize_text(answer) for answer in answers)
    winner_norm, _ = counts.most_common(1)[0]
    for answer in answers:
        if normalize_text(answer) == winner_norm:
            return answer
    return answers[0]


def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


# --------------------------------------------------------------------------- #
# Identity helpers: agent_id -> tradition, the join key to problems.json's
# `expected_strongest_tradition` / `annotations` (both lowercase short_name).
# --------------------------------------------------------------------------- #
def solver_tradition(run: dict[str, Any], solver_role: str) -> str:
    agent_id = run["assigned_roles"]["solver_roles"][solver_role]
    return get_agent(agent_id)["short_name"].lower()


def judge_tradition(run: dict[str, Any]) -> str:
    agent_id = run["assigned_roles"]["judge"]
    return get_agent(agent_id)["short_name"].lower()


def winner_tradition(run: dict[str, Any]) -> str:
    winner_role = run.get("judge_decision", {}).get("winner")
    if not winner_role:
        return ""
    return solver_tradition(run, winner_role)


def traditions_by_solver_role(run: dict[str, Any]) -> dict[str, str]:
    return {role: solver_tradition(run, role) for role in ordered_solver_roles(run)}


# --------------------------------------------------------------------------- #
# Verdict Accuracy + inter-annotator agreement
# --------------------------------------------------------------------------- #
def label_agreement_fraction(problem: dict[str, Any]) -> float:
    """Parse a `label_agreement` string like "2/3" into 0.667."""

    raw = str(problem.get("label_agreement", "")).strip()
    if "/" in raw:
        num, _, den = raw.partition("/")
        try:
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def inter_annotator_agreement_summary(problems: list[dict[str, Any]]) -> dict[str, Any]:
    fractions = [label_agreement_fraction(problem) for problem in problems]
    distribution = Counter(str(problem.get("label_agreement", "")).strip() for problem in problems)
    return {
        "mean_agreement": sum(fractions) / len(fractions) if fractions else 0.0,
        "distribution": dict(distribution),
    }


def verdict_accuracy_rows(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        expected = str(problem.get("expected_strongest_tradition", "")).strip().lower()
        actual = winner_tradition(run)
        rows.append(
            {
                "problem_id": problem["id"],
                "category": problem.get("category", "unknown"),
                "difficulty": problem.get("difficulty", "unknown"),
                "expected_strongest_tradition": expected,
                "winner_tradition": actual,
                "correct": bool(expected) and expected == actual,
                "label_agreement": label_agreement_fraction(problem),
            }
        )
    return rows


def _group_accuracy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(1 for row in rows if row["correct"])
    return {
        "accuracy": correct / len(rows) if rows else 0.0,
        "n": len(rows),
        "correct": correct,
        "mean_label_agreement": sum(row["label_agreement"] for row in rows) / len(rows) if rows else 0.0,
    }


def verdict_accuracy_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    return {
        "overall": _group_accuracy(rows),
        "by_category": {category: _group_accuracy(items) for category, items in sorted(grouped.items())},
    }


# --------------------------------------------------------------------------- #
# Persona Distinctness (LOW convergence is the success condition: personas
# should stay distinct, not collapse into generic agreement)
# --------------------------------------------------------------------------- #
class PersonaConvergence(BaseModel):
    converged: bool
    reasoning: str


def classify_persona_distinctness(question: str, answers: list[str]) -> PersonaConvergence:
    cache_k = llm_cache.cache_key("persona_distinctness", question, *answers)
    cached = llm_cache.get(cache_k)
    if cached is not None:
        return PersonaConvergence.model_validate(cached)

    from pipeline.llm_client import call_llm_model  # deferred: no API key needed to import this module

    system_prompt = """
You are a neutral evaluator, not any philosopher. You are given three
independently-written answers to the same philosophical question, each
written from a different philosophical tradition. Decide whether the three
answers have substantively CONVERGED on the same practical verdict despite
being written from different traditions (regardless of surface wording), or
whether they remain substantively DISTINCT positions.

converged = true only if all three answers would be read as agreeing on the
same practical verdict. If even one answer takes a meaningfully different
stance, converged = false.

Return only valid JSON with exactly this structure:
{"converged": true, "reasoning": "short explanation"}
"""
    answers_block = "\n\n".join(f"Answer {i + 1}:\n{answer}" for i, answer in enumerate(answers))
    user_prompt = f"Question:\n{question}\n\n{answers_block}"
    result = call_llm_model(
        system_prompt, user_prompt, PersonaConvergence, max_output_tokens=800, effort="low"
    )
    llm_cache.put(cache_k, result.model_dump())
    return result


def persona_distinctness_rows(
    problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]], max_workers: int = 8
) -> list[dict[str, Any]]:
    tasks = []
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        answers = initial_answers(run)
        if len(answers) >= 2:
            tasks.append((problem, answers))

    def _classify(task: tuple[dict[str, Any], list[str]]) -> tuple[dict[str, Any], PersonaConvergence]:
        problem, answers = task
        return problem, classify_persona_distinctness(problem["question"], answers)

    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for problem, result in pool.map(_classify, tasks):
            rows.append(
                {
                    "problem_id": problem["id"],
                    "category": problem.get("category", "unknown"),
                    "difficulty": problem.get("difficulty", "unknown"),
                    "converged": result.converged,
                    "reasoning": result.reasoning,
                }
            )
    return rows


def persona_distinctness_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def _rate_by(key: str) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[row[key]].append(row)
        return {
            group: {
                "distinct_rate": sum(1 for r in items if not r["converged"]) / len(items),
                "n": len(items),
            }
            for group, items in sorted(grouped.items())
        }

    n = len(rows)
    n_converged = sum(1 for row in rows if row["converged"])
    return {
        "distinct_rate": (n - n_converged) / n if n else 0.0,
        "n": n,
        "n_converged": n_converged,
        "by_difficulty": _rate_by("difficulty"),
        "by_category": _rate_by("category"),
    }


# --------------------------------------------------------------------------- #
# Judge Reliability
# --------------------------------------------------------------------------- #
def rankings_consistency_rate(runs: dict[str, dict[str, Any]]) -> float:
    """Fraction of runs where `winner == rankings[0]` -- NOT schema-enforced,
    only instructed in the Stage 4 prompt, so this must be measured."""

    total = consistent = 0
    for run in runs.values():
        decision = run.get("judge_decision", {})
        rankings = decision.get("rankings")
        if not rankings:
            continue
        total += 1
        if rankings[0] == decision.get("winner"):
            consistent += 1
    return consistent / total if total else 0.0


def judge_reliability_summary(
    problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]], persona_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Restricted to problems where the solvers are 'clearly opposed' (not
    converged, per the persona-distinctness pass)."""

    opposed_ids = {row["problem_id"] for row in persona_rows if not row["converged"]}
    correct = n_opposed = 0
    for problem in problems:
        if problem["id"] not in opposed_ids:
            continue
        run = runs.get(problem["id"])
        if run is None:
            continue
        n_opposed += 1
        expected = str(problem.get("expected_strongest_tradition", "")).strip().lower()
        if winner_tradition(run) == expected:
            correct += 1
    return {
        "accuracy_on_opposed": correct / n_opposed if n_opposed else 0.0,
        "n_opposed_problems": n_opposed,
        "rankings_consistency_rate": rankings_consistency_rate(runs),
    }


# --------------------------------------------------------------------------- #
# Improvement Rate (order-bias controlled, scoped to the judge's winner)
# --------------------------------------------------------------------------- #
class PairwiseComparison(BaseModel):
    winner: Literal["A", "B", "tie"]
    justification: str


def compare_pair(question: str, text_a: str, text_b: str) -> PairwiseComparison:
    cache_k = llm_cache.cache_key("pairwise_compare", question, text_a, text_b)
    cached = llm_cache.get(cache_k)
    if cached is not None:
        return PairwiseComparison.model_validate(cached)

    from pipeline.llm_client import call_llm_model  # deferred: no API key needed to import this module

    system_prompt = """
You are a neutral philosophy evaluator, not any philosopher. You are given two
answers (A and B) to the same question and must decide which is the stronger
piece of philosophical reasoning -- more internally consistent, better
engages counterarguments, more rigorously argued -- independent of which
position you personally find more persuasive. If they are genuinely
comparable in quality, say "tie". Do not favor length.

Return only valid JSON with exactly this structure:
{"winner": "A", "justification": "short reason"}
"""
    user_prompt = f"Question:\n{question}\n\nAnswer A:\n{text_a}\n\nAnswer B:\n{text_b}"
    result = call_llm_model(
        system_prompt, user_prompt, PairwiseComparison, max_output_tokens=600, effort="low"
    )
    llm_cache.put(cache_k, result.model_dump())
    return result


def pairwise_improvement_for_winner(problem: dict[str, Any], run: dict[str, Any]) -> dict[str, Any] | None:
    """Order-bias controlled: compare_pair runs twice with swapped positions;
    a side only "wins" if it wins both orderings, else it's recorded as a tie."""

    winner_role = run.get("judge_decision", {}).get("winner")
    if not winner_role:
        return None
    initial_text = run.get("initial_solutions", {}).get(winner_role, {}).get("solution", "")
    refined_text = run.get("refinements", {}).get(winner_role, {}).get("refined_solution", "")
    if not initial_text or not refined_text:
        return None

    forward = compare_pair(problem["question"], initial_text, refined_text)  # A=initial, B=refined
    backward = compare_pair(problem["question"], refined_text, initial_text)  # A=refined, B=initial

    def _side(comparison: PairwiseComparison, refined_is_a: bool) -> str:
        if comparison.winner == "tie":
            return "tie"
        return "refined" if (comparison.winner == "A") == refined_is_a else "initial"

    forward_side = _side(forward, refined_is_a=False)
    backward_side = _side(backward, refined_is_a=True)
    position_consistent = forward_side == backward_side

    if position_consistent and forward_side == "refined":
        outcome = "improved"
    elif position_consistent and forward_side == "initial":
        outcome = "regressed"
    else:
        outcome = "tie"

    return {"outcome": outcome, "position_consistent": position_consistent}


def improvement_rate_rows(
    problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]], max_workers: int = 8
) -> list[dict[str, Any]]:
    tasks = [(problem, runs[problem["id"]]) for problem in problems if problem["id"] in runs]

    def _run(task: tuple[dict[str, Any], dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        problem, run = task
        return problem, pairwise_improvement_for_winner(problem, run)

    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for problem, result in pool.map(_run, tasks):
            if result is None:
                continue
            rows.append(
                {
                    "problem_id": problem["id"],
                    "category": problem.get("category", "unknown"),
                    "difficulty": problem.get("difficulty", "unknown"),
                    **result,
                }
            )
    return rows


def improvement_rate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    outcome_counts = Counter(row["outcome"] for row in rows)
    consistent = sum(1 for row in rows if row["position_consistent"])
    return {
        "rate": outcome_counts.get("improved", 0) / n if n else 0.0,
        "regressed_rate": outcome_counts.get("regressed", 0) / n if n else 0.0,
        "tie_rate": outcome_counts.get("tie", 0) / n if n else 0.0,
        "position_consistency_rate": consistent / n if n else 0.0,
        "n": n,
    }


# --------------------------------------------------------------------------- #
# Position Change (pure, from Stage 3 `accepted` flags)
# --------------------------------------------------------------------------- #
def position_change_by_tradition(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tally: dict[str, dict[str, int]] = defaultdict(lambda: {"accepted": 0, "rejected": 0})
    for run in runs.values():
        for solver_role, refinement in run.get("refinements", {}).items():
            tradition = solver_tradition(run, solver_role)
            for change in refinement.get("changes_made", []):
                tally[tradition]["accepted" if change.get("accepted") else "rejected"] += 1
    return {
        tradition: {
            **counts,
            "acceptance_rate": (
                counts["accepted"] / (counts["accepted"] + counts["rejected"])
                if (counts["accepted"] + counts["rejected"])
                else 0.0
            ),
        }
        for tradition, counts in tally.items()
    }


# --------------------------------------------------------------------------- #
# Critique Quality
# --------------------------------------------------------------------------- #
def concat_review_text(review: dict[str, Any]) -> str:
    parts = list(review.get("weaknesses", [])) + list(review.get("suggested_changes", []))
    parts += [error.get("description", "") for error in review.get("errors", [])]
    return " ".join(parts)


def attribute_changes_to_reviewers(
    run: dict[str, Any], target_role: str, threshold: float = 0.35
) -> list[dict[str, Any]]:
    """Fuzzy-match each refinement's critique string against its two
    reviewers' text, to approximate which reviewer's critique was accepted."""

    refinement = run.get("refinements", {}).get(target_role, {})
    reviews = run.get("peer_reviews", {}).get(target_role, {})  # reviewer_role -> review
    attributions = []
    for change in refinement.get("changes_made", []):
        critique_text = change.get("critique", "")
        best_reviewer, best_score = None, 0.0
        for reviewer_role, review in reviews.items():
            score = text_similarity(critique_text, concat_review_text(review))
            if score > best_score:
                best_reviewer, best_score = reviewer_role, score
        if best_reviewer is not None and best_score >= threshold:
            attributions.append(
                {"reviewer_role": best_reviewer, "accepted": bool(change.get("accepted")), "match_score": best_score}
            )
    return attributions


def critique_acceptance_by_reviewer_tradition(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tally: dict[str, dict[str, int]] = defaultdict(lambda: {"accepted": 0, "rejected": 0})
    for run in runs.values():
        for target_role in run.get("refinements", {}):
            for attribution in attribute_changes_to_reviewers(run, target_role):
                reviewer_tradition = solver_tradition(run, attribution["reviewer_role"])
                tally[reviewer_tradition]["accepted" if attribution["accepted"] else "rejected"] += 1
    return {
        tradition: {
            **counts,
            "acceptance_rate": (
                counts["accepted"] / (counts["accepted"] + counts["rejected"])
                if (counts["accepted"] + counts["rejected"])
                else 0.0
            ),
        }
        for tradition, counts in tally.items()
    }


def _all_reviews(runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    all_reviews = []
    for problem_id, run in runs.items():
        for target_role, reviewers in run.get("peer_reviews", {}).items():
            for reviewer_role, review in reviewers.items():
                all_reviews.append(
                    {
                        "problem_id": problem_id,
                        "target_role": target_role,
                        "reviewer_role": reviewer_role,
                        "review": review,
                    }
                )
    return all_reviews


def boilerplate_flags(all_reviews: list[dict[str, Any]], threshold: float = 0.8) -> list[dict[str, Any]]:
    """Near-duplicate review text across the whole run set -- a proxy for
    copy-paste boilerplate rather than genuine, problem-specific critique."""

    texts = [concat_review_text(item["review"]) for item in all_reviews]
    flags = []
    for i in range(len(all_reviews)):
        if not texts[i]:
            continue
        for j in range(i + 1, len(all_reviews)):
            if not texts[j]:
                continue
            score = text_similarity(texts[i], texts[j])
            if score >= threshold:
                flags.append(
                    {
                        "a": {k: all_reviews[i][k] for k in ("problem_id", "reviewer_role", "target_role")},
                        "b": {k: all_reviews[j][k] for k in ("problem_id", "reviewer_role", "target_role")},
                        "similarity": score,
                    }
                )
    return flags


def boilerplate_summary(all_reviews: list[dict[str, Any]], threshold: float = 0.8) -> dict[str, Any]:
    flags = boilerplate_flags(all_reviews, threshold)
    flagged = set()
    for flag in flags:
        flagged.add((flag["a"]["problem_id"], flag["a"]["reviewer_role"], flag["a"]["target_role"]))
        flagged.add((flag["b"]["problem_id"], flag["b"]["reviewer_role"], flag["b"]["target_role"]))
    return {
        "n_reviews": len(all_reviews),
        "n_near_duplicate_pairs": len(flags),
        "n_flagged_reviews": len(flagged),
        "flagged_rate": len(flagged) / len(all_reviews) if all_reviews else 0.0,
    }


def sample_reviews_for_spot_check(all_reviews: list[dict[str, Any]], n: int = 15, seed: int = 42) -> list[dict[str, Any]]:
    """Not automatable -- exports a sample for the team's manual spot-check."""

    rng = random.Random(seed)
    return rng.sample(all_reviews, min(n, len(all_reviews)))


def critique_quality_summary(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "acceptance_by_reviewer_tradition": critique_acceptance_by_reviewer_tradition(runs),
        "boilerplate": boilerplate_summary(_all_reviews(runs)),
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def evaluate(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    from evaluation import baseline, fidelity_rubrics, judge_bias

    persona_rows = persona_distinctness_rows(problems, runs)
    verdict_rows = verdict_accuracy_rows(problems, runs)
    improvement_rows = improvement_rate_rows(problems, runs)
    baseline_rows = baseline.build_baseline_rows(problems, runs)

    summary = {
        "label_agreement": inter_annotator_agreement_summary(problems),
        "verdict_accuracy": verdict_accuracy_summary(verdict_rows),
        "improvement_rate": improvement_rate_summary(improvement_rows),
        "persona_distinctness": persona_distinctness_summary(persona_rows),
        "judge_reliability": judge_reliability_summary(problems, runs, persona_rows),
        "fidelity": fidelity_rubrics.fidelity_summary(problems, runs),
        "position_change": position_change_by_tradition(runs),
        "critique_quality": critique_quality_summary(runs),
        "judge_bias": judge_bias.compute_all(problems, runs),
        "baselines": baseline.baseline_summary(baseline_rows),
    }
    rows_by_name = {
        "verdict_accuracy_rows": verdict_rows,
        "persona_distinctness_rows": persona_rows,
        "improvement_rate_rows": improvement_rows,
        "baseline_rows": baseline_rows,
    }
    return summary, rows_by_name


def save_evaluation(summary: dict[str, Any], rows_by_name: dict[str, list[dict[str, Any]]]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for name, rows in rows_by_name.items():
        (RESULTS_DIR / f"{name}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def main() -> None:
    problems = load_problems()
    runs = load_debate_runs()
    summary, rows_by_name = evaluate(problems, runs)
    save_evaluation(summary, rows_by_name)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
