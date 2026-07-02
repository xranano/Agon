import json
from typing import Any, Dict, List, Optional

from pipeline.agent_registry import AGENT_ORDER, AGENTS, get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import AssignedRoles, SelectorDecision


def assign_roles(
    assessments: List[Dict[str, Any]],
    mode: str = "auto",
    selected_judge: Optional[str] = None,
    selected_solvers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if mode == "selector":
        if selected_judge or selected_solvers:
            return assign_roles_from_selection(selected_judge, selected_solvers)
        return assign_roles_with_selector(assessments)
    if mode != "auto":
        raise ValueError("selection mode must be 'auto' or 'selector'.")
    return assign_roles_auto(assessments)


def assign_roles_auto(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic Stage 0.5 assignment (project-agon spec):

    - Judge: highest Judge confidence wins; ties broken by the smallest
      Solver-Judge confidence gap, then alphabetically by agent name.
    - Sits out: among the four remaining philosophers, whoever has the lowest
      Solver confidence sits out (ties broken alphabetically).
    - Solvers: the other three remaining philosophers, in fixed agent order.
    """

    def agent_name(agent_id: str) -> str:
        return get_agent(agent_id)["name"]

    def judge_sort_key(item: Dict[str, Any]):
        judge_conf = float(item["confidence"].get("Judge", 0.0))
        solver_conf = float(item["confidence"].get("Solver", 0.0))
        gap = abs(solver_conf - judge_conf)
        return (-judge_conf, gap, agent_name(item["agent"]))

    def solver_confidence_sort_key(item: Dict[str, Any]):
        solver_conf = float(item["confidence"].get("Solver", 0.0))
        return (solver_conf, agent_name(item["agent"]))

    judge_item = sorted(assessments, key=judge_sort_key)[0]
    judge_id = judge_item["agent"]

    remaining = [item for item in assessments if item["agent"] != judge_id]
    sits_out_item = sorted(remaining, key=solver_confidence_sort_key)[0]
    sits_out_id = sits_out_item["agent"]

    order_index = {agent_id: index for index, agent_id in enumerate(AGENT_ORDER)}
    solver_ids = sorted(
        (item["agent"] for item in remaining if item["agent"] != sits_out_id),
        key=lambda agent_id: order_index[agent_id],
    )
    if len(solver_ids) != 3:
        raise ValueError(f"auto assignment must produce exactly 3 solvers, got {len(solver_ids)}")

    solver_roles = _solver_roles_from_ids(solver_ids)
    roles = AssignedRoles(
        judge=judge_id,
        solvers=solver_ids,
        solver_roles=solver_roles,
        sits_out=sits_out_id,
        assignment_rule=(
            "judge selected by highest Judge confidence (ties by smallest "
            "Solver-Judge confidence gap, then alphabetically); remaining "
            "philosopher with lowest Solver confidence sits out"
        ),
        selection_mode="auto",
    )
    return roles.model_dump()


def assign_roles_from_selection(
    selected_judge: Optional[str],
    selected_solvers: Optional[List[str]],
) -> Dict[str, Any]:
    if not selected_judge:
        raise ValueError("selector mode requires a selected judge.")
    if not selected_solvers:
        raise ValueError("selector mode requires selected solvers.")

    valid_ids = set(AGENT_ORDER)
    solver_ids = list(dict.fromkeys(selected_solvers))
    if selected_judge not in valid_ids:
        raise ValueError(f"unknown judge id: {selected_judge}")
    if any(agent_id not in valid_ids for agent_id in solver_ids):
        raise ValueError("selected solvers include an unknown agent id.")
    if selected_judge in solver_ids:
        raise ValueError("judge cannot also be selected as a solver.")
    if not 2 <= len(solver_ids) <= 4:
        raise ValueError("selector mode requires between 2 and 4 solvers.")

    roles = AssignedRoles(
        judge=selected_judge,
        solvers=solver_ids,
        solver_roles=_solver_roles_from_ids(solver_ids),
        assignment_rule="judge and solvers selected manually by the user",
        selection_mode="selector",
        selector_reasoning="Manual frontend/CLI selection.",
    )
    return roles.model_dump()


def assign_roles_with_selector(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    system_prompt = """
You are the role selector for a multi-agent debate pipeline.
Pick exactly one judge and between two and four solvers from the available agents.
Use the agents' self-assessments, but prioritize a balanced team with a strong final evaluator.
"""
    user_prompt = f"""
Available agents:
{json.dumps(AGENTS, indent=2)}

Role self-assessments:
{json.dumps(assessments, indent=2)}

Choose the judge and the ordered solver slots. Use solver_1 and solver_2 at minimum; leave solver_3 and/or solver_4 null if they are not needed.
"""
    decision = call_llm_model(system_prompt, user_prompt, SelectorDecision, max_output_tokens=3000)
    solver_ids = [
        agent_id
        for agent_id in [decision.solver_1, decision.solver_2, decision.solver_3, decision.solver_4]
        if agent_id
    ]
    all_ids = [decision.judge, *solver_ids]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("selector must not assign an agent more than once.")
    if not 2 <= len(solver_ids) <= 4:
        raise ValueError("selector must assign between 2 and 4 solvers.")

    roles = AssignedRoles(
        judge=decision.judge,
        solvers=solver_ids,
        solver_roles=_solver_roles_from_ids(solver_ids),
        assignment_rule="judge and solver order selected by selector model from role self-assessments",
        selection_mode="selector",
        selector_reasoning=decision.reasoning,
    )
    return roles.model_dump()


def _solver_roles_from_ids(solver_ids: List[str]) -> Dict[str, str]:
    return {
        f"solver_{index}": agent_id
        for index, agent_id in enumerate(solver_ids, start=1)
    }
