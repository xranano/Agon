from typing import Any, Dict, List
from pipeline.agent_registry import AGENT_ORDER

def assign_roles(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    order_index = {agent_id: index for index, agent_id in enumerate(AGENT_ORDER)}
    def judge_score(item: Dict[str, Any]):
        solver_conf = float(item["confidence"].get("Solver", 0.0))
        judge_conf = float(item["confidence"].get("Judge", 0.0))
        #logic is: 1st-judge advantage, 2nd-judge confidence, 3rd-tie breaker
        return (
            judge_conf - solver_conf,
            judge_conf,
            -order_index[item["agent"]],
        )
    judge_item = max(assessments, key=judge_score)
    judge_id = judge_item["agent"]
    solver_ids = [
        item["agent"]
        for item in sorted(assessments, key=lambda x: order_index[x["agent"]])
        if item["agent"] != judge_id
    ]
    solver_roles = {
        "solver_1": solver_ids[0],
        "solver_2": solver_ids[1],
        "solver_3": solver_ids[2],
    }
    return {
        "judge": judge_id,
        "solvers": solver_ids,
        "solver_roles": solver_roles,
        "assignment_rule": "judge selected by judge-solver confidence advantage; ties broken deterministically by fixed agent order",
    }