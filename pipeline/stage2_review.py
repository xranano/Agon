import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_json

def generate_peer_reviews(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
) -> Dict[str, Any]:

    reviews: Dict[str, Any] = {
        "solver_1": {},
        "solver_2": {},
        "solver_3": {},
    }
    solver_roles = ["solver_1", "solver_2", "solver_3"]

    for reviewer_role in solver_roles:
        reviewer_agent_id = roles["solver_roles"][reviewer_role]
        reviewer_agent = get_agent(reviewer_agent_id)
        for target_role in solver_roles:
            if reviewer_role == target_role:
                continue
            target_solution = solutions[target_role]
            system_prompt = f"""
You are {reviewer_agent["name"]}.
Your reasoning style: {reviewer_agent["style"]}

You are acting as {reviewer_role}.
Your task is to critically review {target_role}'s solution.
Be fair, strict, and specific.
Look for logical errors, calculation mistakes, missing cases, unsupported claims, or unclear reasoning.

Return only valid JSON with exactly this structure:
{{
  "reviewer_role": "{reviewer_role}",
  "target_role": "{target_role}",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "errors": [
    {{
      "location": "where the issue appears",
      "error_type": "logical_error/calculation_error/missing_case/unclear_reasoning/other",
      "description": "what is wrong",
      "severity": "minor/major/critical"
    }}
  ],
  "suggested_changes": ["change 1", "change 2"],
  "overall_assessment": "correct/mostly_correct/promising_but_flawed/incorrect"
}}
"""
            user_prompt = f"""
Original problem:
{problem["question"]}

Solution to review:
{json.dumps(target_solution, indent=2, ensure_ascii=False)}
Review this solution.
"""
            reviews[target_role][reviewer_role] = call_llm_json(
                system_prompt,
                user_prompt,
                max_output_tokens=3000,
            )
    return reviews