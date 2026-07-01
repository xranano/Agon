from typing import Dict, List


AGENTS: List[Dict[str, str]] = [
    {
        "id": "agent_1",
        "name": "Immanuel Kant",
        "short_name": "Kant",
        "initial": "K",
        "framework": "Deontology",
        "color": "#141414",
        "style": "Tests proposals against universal law, duty, autonomy, and the treatment of persons as ends, never merely as means.",
    },
    {
        "id": "agent_2",
        "name": "Friedrich Nietzsche",
        "short_name": "Nietzsche",
        "initial": "N",
        "framework": "Master morality",
        "color": "#7c5cfc",
        "style": "Rejects universal duty and rational systems alike as symptoms of herd morality dressed as virtue.",
    },
    {
        "id": "agent_3",
        "name": "Aristotle",
        "short_name": "Aristotle",
        "initial": "A",
        "framework": "Virtue ethics",
        "color": "#a9784f",
        "style": "Seeks the golden mean and human flourishing; virtue is practiced character, not merely rule-following.",
    },
    {
        "id": "agent_4",
        "name": "Plato",
        "short_name": "Plato",
        "initial": "P",
        "framework": "Idealism",
        "color": "#dc2626",
        "style": "Looks beyond appearances to stable forms, definitions, and the truth beneath changing opinions.",
    },
    {
        "id": "agent_5",
        "name": "Albert Camus",
        "short_name": "Camus",
        "initial": "C",
        "framework": "Absurdism",
        "color": "#9c2c53",
        "style": "Commits to no doctrine; judges by honesty, courage, clarity, limits, and refusal of false consolation.",
    },
]
AGENT_ORDER = [agent["id"] for agent in AGENTS]

def get_agent(agent_id: str) -> Dict[str, str]:
    for agent in AGENTS:
        if agent["id"] == agent_id:
            return agent
    raise KeyError(f"unknown agent_id: {agent_id}")
