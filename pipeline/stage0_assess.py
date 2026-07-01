from typing import Any, Dict, List
from pipeline.agent_registry import AGENTS
from pipeline.llm_client import call_llm_model
from pipeline.schemas import RoleAssessment

def assess_roles(problem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Stage 0:
    Each agent self-assesses whether it is better suited as Solver or Judge.
    """

    assessments: List[Dict[str, Any]] = []

    for agent in AGENTS:
        system_prompt = f"""
You are {agent["name"]}.
Your reasoning style: {agent["style"]}

You are participating in a multi-LLM collaborative debate system.
For the given problem, assess whether you are better suited to be a Solver or a Judge.

Return only valid JSON with exactly this structure:
{{
  "agent": "{agent["id"]}",
  "agent_name": "{agent["name"]}",
  "confidence": {{
    "Solver": 0.0,
    "Judge": 0.0
  }},
  "preferred_role": "Solver or Judge",
  "reasoning": "short explanation"
}}
"""
        user_prompt = f"""
Problem:
{problem["question"]}

Give confidence scores between 0 and 1 for Solver and Judge.
"""
        assessment = call_llm_model(
            system_prompt,
            user_prompt,
            RoleAssessment,
            max_output_tokens=2500,
        )
        assessments.append(assessment.model_dump())
    return assessments
