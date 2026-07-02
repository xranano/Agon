import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import PeerReview

def generate_peer_reviews(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
) -> Dict[str, Any]:

    solver_roles = list(roles["solver_roles"].keys())
    reviews: Dict[str, Any] = {solver_role: {} for solver_role in solver_roles}

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
Your task is to critically review {target_role}'s answer to a philosophical question.
Be fair, strict, and specific. Judge the reasoning, not the writing style.
Look for: unsupported or overstated claims, ignored counterarguments, misattributed or
misstated philosophers' positions, framework confusion, equivocation, incoherence, or a
verdict that does not follow from the argument. Note genuine strengths too.
Be concise. Use at most 2 strengths, 2 weaknesses, 2 errors, and 2 suggested changes.
Each list item must be one short sentence.

Return only valid JSON with exactly this structure:
{{
  "reviewer_role": "{reviewer_role}",
  "target_role": "{target_role}",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "errors": [
    {{
      "location": "which claim or step",
      "error_type": "unsupported_claim/ignored_counterargument/misattributed_view/framework_confusion/incoherence/other",
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
            review = call_llm_model(
                system_prompt,
                user_prompt,
                PeerReview,
                max_output_tokens=3000,
            )
            reviews[target_role][reviewer_role] = review.model_dump()
    return reviews
