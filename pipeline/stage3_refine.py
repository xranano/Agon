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
You already gave an initial solution and now received peer reviews.
Address each critique explicitly.
Accept valid critiques and revise your solution.
Reject invalid critiques only if you clearly justify why.
Be concise and structured. Limit changes_made to at most 3 items.
Limit refined_solution to 3-5 short numbered points, each one sentence.
Do not write an essay.

Return only valid JSON with exactly this structure:
{{
  "solver_role": "{solver_role}",
  "agent_id": "{agent_id}",
  "agent_name": "{agent["name"]}",
  "changes_made": [
    {{
      "critique": "summary of critique",
      "response": "concise response to the critique",
      "accepted": true
    }}
  ],
  "refined_solution": "3-5 short numbered points, each one sentence",
  "refined_answer": "final answer in one sentence",
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
