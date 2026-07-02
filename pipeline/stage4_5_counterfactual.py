from typing import Any, Dict

from pipeline.agent_registry import AGENT_ORDER
from pipeline.stage4_judge import judge_as


def run_counterfactual_judging(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
    refinements: Dict[str, Any],
) -> Dict[str, Any]:
    """Stage 4.5 (evaluation-only): every philosopher OTHER than the assigned
    judge re-judges the identical frozen bundle (original solutions, peer
    reviews, refined solutions) using the identical Stage 4 judge prompt.

    This produces 4 extra verdicts per problem. Combined with the real Stage 4
    verdict (already computed, not re-run here to avoid a redundant API call),
    that is 5 verdicts per problem on identical inputs where judge identity is
    the only variable -- the causal basis for the Judge-Bias Analysis.
    """
    assigned_judge_id = roles["judge"]
    solver_roles = roles["solver_roles"]

    counterfactual_verdicts: Dict[str, Any] = {}
    for agent_id in AGENT_ORDER:
        if agent_id == assigned_judge_id:
            continue
        counterfactual_verdicts[agent_id] = judge_as(
            problem,
            agent_id,
            solver_roles,
            solutions,
            reviews,
            refinements,
        )
    return counterfactual_verdicts


def build_verdict_bundle(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    judge_decision: Dict[str, Any],
    counterfactual_verdicts: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the full 5-verdict bundle (spec's Stage 4.5 output shape)."""
    assigned_judge_id = roles["judge"]
    verdicts = {assigned_judge_id: judge_decision, **counterfactual_verdicts}
    return {
        "problem_id": problem.get("id"),
        "assigned_judge": assigned_judge_id,
        "verdicts": verdicts,
    }
