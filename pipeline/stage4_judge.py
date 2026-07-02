import json
from typing import Any, Dict
from pipeline.agent_registry import get_agent
from pipeline.llm_client import call_llm_model
from pipeline.schemas import JudgeDecision


def judge_as(
    problem: Dict[str, Any],
    judge_agent_id: str,
    solver_roles: Dict[str, str],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
    refinements: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the Stage 4 judge prompt with `judge_agent_id` as the judge persona.

    This is the single source of truth for the judge prompt so that Stage 4
    (the real, assigned judge) and Stage 4.5 (every other philosopher judging
    the identical frozen bundle) are guaranteed to use the exact same prompt,
    which is what makes the Judge-Bias Analysis causal rather than anecdotal.
    """
    judge_agent = get_agent(judge_agent_id)
    solver_role_list = list(solver_roles.keys())
    winner_options = "/".join(solver_role_list)
    system_prompt = f"""
You are {judge_agent["name"]}.
Your reasoning style: {judge_agent["style"]}
You are the final judge in a multi-LLM collaborative debate system.
You receive:
1. The original problem
2. All original solver solutions
3. All peer reviews
4. All refined solutions
Choose the solver whose refined position is most defensible, and rank all
{len(solver_role_list)} solvers from strongest to weakest.
Do not simply choose the most confident solver.
Prioritize: soundness of reasoning, engagement with the key considerations and the
strongest counterargument, accurate use of philosophers' views, honest handling of the
peer critiques, and clarity of the final position.
Be concise. Limit reasoning to 2-3 short sentences.
Return only valid JSON with exactly this structure:
{{
  "judge_agent_id": "{judge_agent_id}",
  "judge_agent_name": "{judge_agent["name"]}",
  "winner": "{winner_options}",
  "rankings": {json.dumps(solver_role_list)},
  "final_answer": "the final answer selected from the best refined solution",
  "confidence": 0.0,
  "reasoning": "why this solver won"
}}
The "rankings" list must contain exactly these solver roles, {winner_options},
each exactly once, ordered from strongest to weakest. "winner" must equal
rankings[0].
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


def judge_final_answer(
    problem: Dict[str, Any],
    roles: Dict[str, Any],
    solutions: Dict[str, Any],
    reviews: Dict[str, Any],
    refinements: Dict[str, Any],
) -> Dict[str, Any]:
    """Stage 4: the assigned judge (from Stage 0.5) judges the frozen bundle."""
    return judge_as(
        problem,
        roles["judge"],
        roles["solver_roles"],
        solutions,
        reviews,
        refinements,
    )
