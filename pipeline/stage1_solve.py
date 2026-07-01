from typing import Any, Dict

from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import SolverSolution


def generate_solutions(problem: Dict[str, Any], roles: Dict[str, Any]) -> Dict[str, Any]:
    solutions: Dict[str, Any] = {}

    for solver_role, agent_id in roles["solver_roles"].items():
        agent = get_agent(agent_id)
        system_prompt = f"""
You are {agent["name"]}.
Your reasoning style: {agent["style"]}
You are acting as {solver_role} in a multi-LLM collaborative debate system.
Solve the problem independently.
Do not mention or assume anything about other solvers.
Be concise and structured. Limit the solution to 3-5 short numbered points.
Each point must be one sentence. Do not write an essay.

Return only valid JSON with exactly this structure:
{{
  "solver_role": "{solver_role}",
  "agent_id": "{agent_id}",
  "agent_name": "{agent["name"]}",
  "solution": "3-5 short numbered points, each one sentence",
  "answer": "final answer in one sentence",
  "confidence": 0.0
}}
"""
        user_prompt = f"""
Problem:
{problem["question"]}
Solve the problem carefully, but keep the response brief and easy to scan.
"""
        solution = call_llm_model(
            system_prompt,
            user_prompt,
            SolverSolution,
            max_output_tokens=3000,
        )
        solutions[solver_role] = solution.model_dump()
    return solutions
