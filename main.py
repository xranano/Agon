import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from config import DATA_DIR, RESULTS_DIR
from pipeline.stage0_assess import assess_roles
from pipeline.stage0_5_assign import assign_roles
from pipeline.stage1_solve import generate_solutions
from pipeline.stage2_review import generate_peer_reviews
from pipeline.stage3_refine import refine_solutions
from pipeline.stage4_judge import judge_final_answer

def load_problems(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        problems = json.load(file)
    if not isinstance(problems, list):
        raise ValueError("problems.json must contain a list of problems.")
    return problems

def save_runs(runs: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(runs, file, indent=2, ensure_ascii=False)

def run_single_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    role_assessments = assess_roles(problem)
    assigned_roles = assign_roles(role_assessments)
    initial_solutions = generate_solutions(problem, assigned_roles)
    peer_reviews = generate_peer_reviews(problem, assigned_roles, initial_solutions)
    refinements = refine_solutions(
        problem,
        assigned_roles,
        initial_solutions,
        peer_reviews,
    )
    judge_decision = judge_final_answer(
        problem,
        assigned_roles,
        initial_solutions,
        peer_reviews,
        refinements,
    )
    return {
        "problem_id": problem.get("id"),
        "category": problem.get("category"),
        "difficulty": problem.get("difficulty"),
        "question": problem.get("question"),
        "expected_answer": problem.get("expected_answer"),
        "grading_notes": problem.get("grading_notes"),
        "role_assessments": role_assessments,
        "assigned_roles": assigned_roles,
        "initial_solutions": initial_solutions,
        "peer_reviews": peer_reviews,
        "refinements": refinements,
        "judge_decision": judge_decision,
        "winner": judge_decision.get("winner"),
        "final_answer": judge_decision.get("final_answer"),
    }

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the existentiAIsm multi-LLM collaborative debate pipeline."
    )
    parser.add_argument(
        "--problems",
        type=Path,
        default=DATA_DIR / "problems.json",
        help="Path to problems JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_DIR / "debate_runs.json",
        help="Path where debate results will be saved.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of problems to run.",
    )
    args = parser.parse_args()
    problems = load_problems(args.problems)

    if args.limit is not None:
        problems = problems[: args.limit]
    print(f"Loaded {len(problems)} problem(s).")
    print(f"Results will be saved to: {args.output}")
    runs: List[Dict[str, Any]] = []

    for index, problem in enumerate(problems, start=1):
        print("=" * 80)
        print(f"Running problem {index}/{len(problems)}: {problem.get('id')}")
        run = run_single_problem(problem)
        runs.append(run)

        # Save after every problem so progress is not lost if a later API call fails.
        save_runs(runs, args.output)
        print(f"Saved result for problem: {problem.get('id')}")
    print("=" * 80)
    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()