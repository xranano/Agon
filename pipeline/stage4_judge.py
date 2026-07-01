import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import JudgeDecision

def judge_final_answer(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
    refinements: Dict[str, Any],
) -> Dict[str, Any]:
    judge_agent = get_agent(roles["judge"])
    winner_options = "/".join(roles["solver_roles"].keys())
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
Be concise. Limit reasoning to 2-3 short sentences.
Return only valid JSON with exactly this structure:
{{
  "judge_agent_id": "{roles["judge"]}",
  "judge_agent_name": "{judge_agent["name"]}",
  "winner": "{winner_options}",
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
    decision = call_llm_model(
        system_prompt,
        user_prompt,
        JudgeDecision,
        max_output_tokens=3000,
    )
    return decision.model_dump()
