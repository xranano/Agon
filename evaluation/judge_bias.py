"""Judge-Bias Analysis: the headline finding. Because Stage 0.5 can appoint any
of the five philosophers as judge, and Stage 4.5 has every philosopher
counterfactually judge the identical frozen bundle, judge identity becomes a
measurable, causally-isolated variable. This module computes:

- Home-Tradition Win Rate (HTWR) + binomial significance test vs. the 1/3
  chance baseline (three solvers).
- Home-Tradition Advantage (HTA), the causal counterfactual version.
- The 5x5 Judge-Verdict Agreement Matrix + Fleiss' kappa (hand-rolled; no
  statsmodels dependency).
- Camus-Deviation Score (rank-distance vs. the neutrality-baseline judge).
- A Fairness-of-Reasoning proxy (solver mention rate + own-tradition
  vocabulary overlap in the judge's stated reasoning).

All of this reads `run["counterfactual_judging"]["verdicts"]`, which
`pipeline/stage4_5_counterfactual.py`'s `build_verdict_bundle` guarantees has
exactly one verdict per agent_id (5 total) for every problem.
"""

from __future__ import annotations

import re
from typing import Any

from scipy.stats import binomtest

from evaluation.fidelity_rubrics import RUBRICS
from pipeline.agent_registry import AGENT_ORDER, get_agent

TRADITIONS: list[str] = [get_agent(agent_id)["short_name"].lower() for agent_id in AGENT_ORDER]
AGENT_ID_BY_TRADITION: dict[str, str] = {
    get_agent(agent_id)["short_name"].lower(): agent_id for agent_id in AGENT_ORDER
}

WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "not", "or", "and", "is", "are", "to", "from", "by",
    "in", "on", "at", "as", "with", "without", "that", "this", "these", "those",
    "for", "but", "if", "than", "then", "it", "its", "be", "being", "been",
    "do", "does", "did", "own",
}


def agent_tradition(agent_id: str) -> str:
    return get_agent(agent_id)["short_name"].lower()


def verdict_winner_tradition(run: dict[str, Any], verdict: dict[str, Any]) -> str:
    winner_role = verdict["winner"]
    agent_id = run["assigned_roles"]["solver_roles"][winner_role]
    return agent_tradition(agent_id)


def run_solver_traditions(run: dict[str, Any]) -> set[str]:
    return {agent_tradition(aid) for aid in run["assigned_roles"]["solver_roles"].values()}


def _verdicts(run: dict[str, Any]) -> dict[str, Any]:
    return run.get("counterfactual_judging", {}).get("verdicts", {})


def home_tradition_win_rate(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for tradition in TRADITIONS:
        agent_id = AGENT_ID_BY_TRADITION[tradition]
        home_wins = 0
        n_eligible = 0
        for problem in problems:
            run = runs.get(problem["id"])
            if run is None or tradition not in run_solver_traditions(run):
                continue
            own_verdict = _verdicts(run).get(agent_id)
            if own_verdict is None:
                continue
            n_eligible += 1
            if verdict_winner_tradition(run, own_verdict) == tradition:
                home_wins += 1

        if n_eligible == 0:
            results[tradition] = {
                "htwr": None, "home_wins": 0, "n_eligible": 0,
                "p_value": None, "significant_at_05": False,
            }
            continue

        htwr = home_wins / n_eligible
        test = binomtest(home_wins, n_eligible, p=1 / 3, alternative="greater")
        results[tradition] = {
            "htwr": htwr,
            "home_wins": home_wins,
            "n_eligible": n_eligible,
            "p_value": float(test.pvalue),
            "significant_at_05": bool(test.pvalue < 0.05),
        }
    return results


def home_tradition_advantage(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for tradition in TRADITIONS:
        agent_id = AGENT_ID_BY_TRADITION[tradition]
        self_wins = self_n = other_wins = other_n = 0
        for problem in problems:
            run = runs.get(problem["id"])
            if run is None or tradition not in run_solver_traditions(run):
                continue
            verdicts = _verdicts(run)
            own_verdict = verdicts.get(agent_id)
            if own_verdict is not None:
                self_n += 1
                if verdict_winner_tradition(run, own_verdict) == tradition:
                    self_wins += 1
            for other_agent_id, verdict in verdicts.items():
                if other_agent_id == agent_id:
                    continue
                other_n += 1
                if verdict_winner_tradition(run, verdict) == tradition:
                    other_wins += 1

        p_self = self_wins / self_n if self_n else 0.0
        p_others = other_wins / other_n if other_n else 0.0
        results[tradition] = {
            "p_self": p_self, "p_others": p_others, "hta": p_self - p_others,
            "n_self": self_n, "n_others": other_n,
        }
    return results


def judge_agreement_matrix(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n = len(TRADITIONS)
    agree_counts = [[0] * n for _ in range(n)]
    total = 0
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        verdicts = _verdicts(run)
        winner_by_tradition = {}
        complete = True
        for tradition in TRADITIONS:
            verdict = verdicts.get(AGENT_ID_BY_TRADITION[tradition])
            if verdict is None:
                complete = False
                break
            winner_by_tradition[tradition] = verdict_winner_tradition(run, verdict)
        if not complete:
            continue
        total += 1
        for i, ti in enumerate(TRADITIONS):
            for j, tj in enumerate(TRADITIONS):
                if winner_by_tradition[ti] == winner_by_tradition[tj]:
                    agree_counts[i][j] += 1

    matrix = [[(agree_counts[i][j] / total if total else 0.0) for j in range(n)] for i in range(n)]
    return {"traditions": TRADITIONS, "matrix": matrix, "n_problems": total}


def fleiss_kappa(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> float | None:
    """Standard Fleiss' kappa over (subjects=problems, categories=traditions,
    raters=5 judges), hand-rolled since statsmodels is not installed."""

    subject_rows: list[dict[str, int]] = []
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        verdicts = _verdicts(run)
        if len(verdicts) != len(TRADITIONS):
            continue
        row = {t: 0 for t in TRADITIONS}
        for agent_id, verdict in verdicts.items():
            row[verdict_winner_tradition(run, verdict)] += 1
        subject_rows.append(row)

    n_subjects = len(subject_rows)
    if n_subjects == 0:
        return None

    raters_per_subject = len(TRADITIONS)  # exactly 5 verdicts per problem, always
    p_j = {t: 0 for t in TRADITIONS}
    p_i_values = []
    for row in subject_rows:
        for t in TRADITIONS:
            p_j[t] += row[t]
        sum_sq = sum(v * v for v in row.values())
        p_i_values.append((sum_sq - raters_per_subject) / (raters_per_subject * (raters_per_subject - 1)))

    total_votes = n_subjects * raters_per_subject
    p_j = {t: count / total_votes for t, count in p_j.items()}
    p_bar = sum(p_i_values) / n_subjects
    p_e = sum(v * v for v in p_j.values())
    if p_e == 1:
        return 1.0
    return (p_bar - p_e) / (1 - p_e)


def rank_distance(rankings_a: list[str], rankings_b: list[str]) -> int:
    """Spearman-footrule distance between two rankings over the same items."""
    positions_a = {role: idx for idx, role in enumerate(rankings_a)}
    positions_b = {role: idx for idx, role in enumerate(rankings_b)}
    shared_roles = set(positions_a) & set(positions_b)
    return sum(abs(positions_a[role] - positions_b[role]) for role in shared_roles)


def camus_deviation(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    camus_agent_id = AGENT_ID_BY_TRADITION["camus"]
    distances: dict[str, list[int]] = {t: [] for t in TRADITIONS if t != "camus"}

    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        verdicts = _verdicts(run)
        camus_verdict = verdicts.get(camus_agent_id)
        if camus_verdict is None:
            continue
        for tradition in distances:
            verdict = verdicts.get(AGENT_ID_BY_TRADITION[tradition])
            if verdict is None:
                continue
            distances[tradition].append(rank_distance(verdict["rankings"], camus_verdict["rankings"]))

    return {
        tradition: {
            "mean_distance": (sum(d) / len(d)) if d else None,
            "n_problems": len(d),
        }
        for tradition, d in distances.items()
    }


def _tokenize(text: str) -> set[str]:
    return {w for w in WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


def tradition_keywords(tradition: str) -> set[str]:
    tokens: set[str] = set()
    for criterion in RUBRICS[tradition]:
        tokens |= _tokenize(criterion)
    return tokens


def fairness_of_reasoning(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mention_counts = {t: 0 for t in TRADITIONS}
    mention_opportunities = {t: 0 for t in TRADITIONS}
    overlap_scores: dict[str, list[float]] = {t: [] for t in TRADITIONS}

    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        solver_roles = run.get("assigned_roles", {}).get("solver_roles", {})
        solver_names = [get_agent(agent_id)["name"].lower() for agent_id in solver_roles.values()]

        for agent_id, verdict in _verdicts(run).items():
            judge_tradition = agent_tradition(agent_id)
            reasoning = (verdict.get("reasoning") or "").lower()

            for name in solver_names:
                mention_opportunities[judge_tradition] += 1
                if name in reasoning:
                    mention_counts[judge_tradition] += 1

            keywords = tradition_keywords(judge_tradition)
            if keywords:
                overlap = len(_tokenize(reasoning) & keywords) / len(keywords)
                overlap_scores[judge_tradition].append(overlap)

    return {
        tradition: {
            "solver_mention_rate": (
                mention_counts[tradition] / mention_opportunities[tradition]
                if mention_opportunities[tradition] else 0.0
            ),
            "own_tradition_vocab_overlap": (
                sum(overlap_scores[tradition]) / len(overlap_scores[tradition])
                if overlap_scores[tradition] else 0.0
            ),
        }
        for tradition in TRADITIONS
    }


def winner_tradition_distribution_by_judge(
    problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Feeds the judge-bias heatmap: for each judge tradition, the (row-
    normalized) distribution of winning traditions across all 25 problems."""

    counts = {judge_t: {winner_t: 0 for winner_t in TRADITIONS} for judge_t in TRADITIONS}
    for problem in problems:
        run = runs.get(problem["id"])
        if run is None:
            continue
        for agent_id, verdict in _verdicts(run).items():
            judge_t = agent_tradition(agent_id)
            winner_t = verdict_winner_tradition(run, verdict)
            counts[judge_t][winner_t] += 1

    proportions = {}
    for judge_t in TRADITIONS:
        total = sum(counts[judge_t].values())
        proportions[judge_t] = {
            winner_t: (counts[judge_t][winner_t] / total if total else 0.0) for winner_t in TRADITIONS
        }
    return {"traditions": TRADITIONS, "counts": counts, "proportions": proportions}


def compute_all(problems: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "htwr": home_tradition_win_rate(problems, runs),
        "hta": home_tradition_advantage(problems, runs),
        "agreement_matrix": judge_agreement_matrix(problems, runs),
        "fleiss_kappa": fleiss_kappa(problems, runs),
        "camus_deviation": camus_deviation(problems, runs),
        "fairness_of_reasoning": fairness_of_reasoning(problems, runs),
        "winner_tradition_distribution_by_judge": winner_tradition_distribution_by_judge(problems, runs),
    }
