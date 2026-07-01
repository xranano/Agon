import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_json

def judge_final_answer(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
    refinements: Dict[str, Any],
) -> Dict[str, Any]:
    judge_agent = get_agent(roles["judge"])
    system_prompt = f"""
You are {judge_agent["name"]}.
Your reasoning style: {judge_agent["style"]}
You are the final judge in a multi-LLM collaborative debate system.
You receive:
1. The original problem
2. All original solver solutions
3. All peer reviews
4. All refined solutions
Choose the solver with the strongest final answer.
Do not simply choose the most confident solver.
Prioritize correctness, reasoning quality, handling of critiques, and final answer clarity.
Return only valid JSON with exactly this structure:
{{
  "judge_agent_id": "{roles["judge"]}",
  "judge_agent_name": "{judge_agent["name"]}",
  "winner": "solver_1/solver_2/solver_3",
  "final_answer": "the final answer selected from the best refined solution",
  "confidence": 0.0,
  "reasoning": "why this solver won"
}}
"""
    user_prompt = f"""
Original problem:
{problem["question"]}
Original solutions:
{json.dumps(solutions, indent=2, ensure_ascii=False)}
Peer reviews:
{json.dumps(reviews, indent=2, ensure_ascii=False)}
Refined solutions:
{json.dumps(refinements, indent=2, ensure_ascii=False)}
Make the final judgment.
"""
    return call_llm_json(system_prompt, user_prompt, max_output_tokens=4000)