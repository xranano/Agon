from typing import Any, Dict

from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_json


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

Return only valid JSON with exactly this structure:
{{
  "solver_role": "{solver_role}",
  "agent_id": "{agent_id}",
  "agent_name": "{agent["name"]}",
  "solution": "step-by-step reasoning",
  "answer": "final concise answer",
  "confidence": 0.0
}}
"""
        user_prompt = f"""
Problem:
{problem["question"]}
Solve the problem carefully.
"""
        solutions[solver_role] = call_llm_json(system_prompt, user_prompt, max_output_tokens=3000)
    return solutions