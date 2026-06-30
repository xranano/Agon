"""Stage 0.5: deterministic role assignment."""


def assign_roles(assessments: list[dict]) -> dict:
    judge = max(
        assessments,
        key=lambda item: (
            item["confidence"]["Judge"],
            -(item["confidence"]["Solver"] - item["confidence"]["Judge"]),
            item["agent"],
        ),
    )
    solvers = sorted(
        [item["agent"] for item in assessments if item["agent"] != judge["agent"]]
    )
    return {"judge": judge["agent"], "solvers": solvers}

