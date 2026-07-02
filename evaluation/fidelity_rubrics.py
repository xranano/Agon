"""Fidelity rubric scoring: does each philosopher's solution stay true to its
actual tradition, or drift into generic reasoning? A persona-free LLM grader
scores each solution against a per-tradition checklist of binary criteria
(copied verbatim from project-agon.md's Argument-Quality Metrics section).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pydantic import BaseModel

from evaluation import llm_cache
from pipeline.agent_registry import get_agent

RUBRICS: dict[str, list[str]] = {
    "kant": [
        "Invokes universalizability or the humanity formula",
        "Justifies via duty, not outcomes",
        "Avoids consequentialist cost-benefit language",
        "Treats persons as ends",
    ],
    "nietzsche": [
        "Distinguishes master/slave morality or names ressentiment",
        "Evaluates by life-affirmation/strength, not universal rules",
        "Rejects appeal to universal duty",
        "Voice is evaluative, not neutral",
    ],
    "aristotle": [
        "Names the relevant virtue(s) and the mean between extremes",
        "Argues from eudaimonia/flourishing",
        "Attends to character and habituation, not just the act",
    ],
    "plato": [
        "Appeals to Forms or an ideal standard beyond appearances",
        "Distinguishes opinion from knowledge",
        "Argues from the ordered soul or ideal state",
    ],
    "camus": [
        "Refuses systematic doctrine",
        "Names the absurd or the demand for honesty/lucidity",
        "Prioritizes clear-eyed confrontation over consoling answers",
    ],
}


class FidelityCriterion(BaseModel):
    criterion: str
    met: bool
    evidence: str


class FidelityScore(BaseModel):
    tradition: str
    criteria_results: list[FidelityCriterion]


def solver_tradition(run: dict[str, Any], solver_role: str) -> str:
    agent_id = run["assigned_roles"]["solver_roles"][solver_role]
    return get_agent(agent_id)["short_name"].lower()


def fidelity_numeric_score(result: FidelityScore) -> float:
    if not result.criteria_results:
        return 0.0
    return sum(1 for c in result.criteria_results if c.met) / len(result.criteria_results)


def score_fidelity(tradition: str, text: str) -> FidelityScore:
    tradition = tradition.lower()
    criteria = RUBRICS[tradition]

    cache_k = llm_cache.cache_key("fidelity", tradition, text)
    cached = llm_cache.get(cache_k)
    if cached is not None:
        return FidelityScore.model_validate(cached)

    system_prompt = f"""
You are a neutral philosophy grader, not any philosopher. You check whether a
piece of reasoning genuinely stays inside the {tradition.title()} tradition,
or drifts into generic reasoning that could belong to any tradition.

For EACH criterion below, decide whether the text satisfies it (true/false)
and cite the specific phrase or move as evidence (or note its absence if not
met). Be strict: a criterion is met only if the text clearly does it, not
merely if the text is compatible with it.

Criteria:
{chr(10).join(f"- {c}" for c in criteria)}

Return only valid JSON with exactly this structure:
{{
  "tradition": "{tradition}",
  "criteria_results": [
    {{"criterion": "<criterion text, verbatim>", "met": true, "evidence": "<quote or absence note>"}}
  ]
}}
There must be exactly one entry per criterion listed above, in the same order.
"""
    from pipeline.llm_client import call_llm_model  # deferred: avoid requiring OPENAI_API_KEY at import time

    user_prompt = f"Text to grade:\n{text}"
    result = call_llm_model(
        system_prompt,
        user_prompt,
        FidelityScore,
        max_output_tokens=2000,
        effort="low",
    )
    llm_cache.put(cache_k, result.model_dump())
    return result


def fidelity_summary(
    problems: list[dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    max_workers: int = 8,
) -> dict[str, Any]:
    """Score every solver's Stage 1 (`solution`) and Stage 3 (`refined_solution`)
    reasoning text against its tradition's rubric, aggregated per tradition."""

    tasks: list[tuple[str, str, str]] = []  # (tradition, stage, text)
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        for solver_role in run.get("assigned_roles", {}).get("solver_roles", {}):
            tradition = solver_tradition(run, solver_role)
            initial = run.get("initial_solutions", {}).get(solver_role, {})
            refined = run.get("refinements", {}).get(solver_role, {})
            if initial.get("solution"):
                tasks.append((tradition, "stage1", initial["solution"]))
            if refined.get("refined_solution"):
                tasks.append((tradition, "stage3", refined["refined_solution"]))

    def _score(task: tuple[str, str, str]) -> tuple[str, str, float]:
        tradition, stage, text = task
        return tradition, stage, fidelity_numeric_score(score_fidelity(tradition, text))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(_score, tasks))

    by_tradition: dict[str, dict[str, list[float]]] = {}
    for tradition, stage, score in results:
        by_tradition.setdefault(tradition, {"stage1": [], "stage3": []})[stage].append(score)

    summary: dict[str, Any] = {}
    for tradition, stages in by_tradition.items():
        stage1_scores, stage3_scores = stages["stage1"], stages["stage3"]
        stage1_mean = sum(stage1_scores) / len(stage1_scores) if stage1_scores else 0.0
        stage3_mean = sum(stage3_scores) / len(stage3_scores) if stage3_scores else 0.0
        summary[tradition] = {
            "stage1": stage1_mean,
            "stage3": stage3_mean,
            "delta": stage3_mean - stage1_mean,
            "n": len(stage1_scores),
        }
    return summary
