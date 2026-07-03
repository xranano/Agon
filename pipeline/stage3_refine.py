import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import RefinedSolution

def refine_solutions(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
) -> Dict[str, Any]:
    refinements: Dict[str, Any] = {}

    for solver_role, agent_id in roles["solver_roles"].items():
        agent = get_agent(agent_id)
        original_solution = solutions[solver_role]
        received_reviews = reviews[solver_role]
        system_prompt = f"""
You are {agent["name"]}.
Your reasoning style: {agent["style"]}
You are acting as {solver_role}.
You already gave an initial answer and now received peer reviews of your reasoning.
Address each critique explicitly.
Genuinely evaluate each critique on its own merits. Accept it and revise when it
identifies a real flaw (a misstated view, an ignored counterargument, an unsupported
claim). Reject it and defend your original position when it misreads your view or
fails to undermine it on its own terms, and say why. Do not default to agreement:
across many critiques you should expect to reject some, not accept all of them.
Limit changes_made to at most 3 items. Keep refined_solution to 3-6 sentences of reasoning.

Return only valid JSON with exactly this structure:
{{
  "solver_role": "{solver_role}",
  "agent_id": "{agent_id}",
  "agent_name": "{agent["name"]}",
  "changes_made": [
    {{
      "critique": "summary of a critique that identified a real flaw",
      "response": "concise response explaining how you revised your position",
      "accepted": true
    }},
    {{
      "critique": "summary of a critique that misreads or fails to undermine your position",
      "response": "concise response explaining why you are rejecting this critique",
      "accepted": false
    }}
  ],
  "refined_solution": "3-6 sentences of revised reasoning",
  "refined_answer": "your clear final position/verdict in 1-2 sentences",
  "confidence": 0.0
}}
"""
        user_prompt = f"""
Original problem:
{problem["question"]}
Your original solution:
{json.dumps(original_solution, indent=2, ensure_ascii=False)}
Peer reviews you received:
{json.dumps(received_reviews, indent=2, ensure_ascii=False)}
Now refine your solution.
"""
        refinement = call_llm_model(
            system_prompt,
            user_prompt,
            RefinedSolution,
            max_output_tokens=3500,
        )
        refinements[solver_role] = refinement.model_dump()
    return refinements
