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
You are acting as {solver_role} in a multi-agent philosophical debate.
Give your own reasoned answer to the philosophical question, independently.
Do not mention or assume anything about other solvers.

Argue like a philosopher, not a calculator:
- name the framework or lens you reason from,
- engage the key considerations and the strongest counterargument,
- then commit to a clear, defensible position (do not sit on the fence).
Be substantive but disciplined: 3-6 sentences of reasoning, no padding.

Return only valid JSON with exactly this structure:
{{
  "solver_role": "{solver_role}",
  "agent_id": "{agent_id}",
  "agent_name": "{agent["name"]}",
  "solution": "3-6 sentences of reasoning: framework, key considerations, strongest objection",
  "answer": "your clear position/verdict in 1-2 sentences",
  "confidence": 0.0
}}
"""
        user_prompt = f"""
Philosophical question:
{problem["question"]}
Reason carefully and take a clear, defensible position.
"""
        solution = call_llm_model(
            system_prompt,
            user_prompt,
            SolverSolution,
            max_output_tokens=3000,
        )
        solutions[solver_role] = solution.model_dump()
    return solutions
