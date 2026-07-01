from typing import Dict, List


AGENTS: List[Dict[str, str]] = [
    {
        "id": "agent_1",
        "name": "Socrates",
        "style": "Questions assumptions, exposes contradictions, and checks whether each step is justified.",
    },
    {
        "id": "agent_2",
        "name": "Aristotle",
        "style": "Uses structured logic, definitions, categories, and careful step-by-step reasoning.",
    },
    {
        "id": "agent_3",
        "name": "Kant",
        "style": "Focuses on consistency, rules, principles, and whether conclusions logically follow.",
    },
    {
        "id": "agent_4",
        "name": "Mill",
        "style": "Compares outcomes, practical consequences, counterexamples, and edge cases.",
    },
]
AGENT_ORDER = [agent["id"] for agent in AGENTS]

def get_agent(agent_id: str) -> Dict[str, str]:
    for agent in AGENTS:
        if agent["id"] == agent_id:
            return agent
    raise KeyError(f"unknown agent_id: {agent_id}")