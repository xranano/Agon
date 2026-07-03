"""One-off: re-run Stage 3 onward with the de-anchored prompt, reusing cached
Stage 1/2 output from an existing debate_runs.json so we don't re-spend API
calls on initial_solutions/peer_reviews, which don't depend on the Stage 3
prompt fix.

Usage:
    python scripts/rerun_refinement.py [--input results/debate_runs.json] [--output results/debate_runs_v2.json] [--limit N]
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from config import RESULTS_DIR
from pipeline.stage3_refine import refine_solutions
from pipeline.stage4_judge import judge_final_answer
from pipeline.stage4_5_counterfactual import build_verdict_bundle, run_counterfactual_judging


def rerun_one(run: Dict[str, Any]) -> Dict[str, Any]:
    problem = run["problem"]
    roles = run["assigned_roles"]
    initial_solutions = run["initial_solutions"]
    peer_reviews = run["peer_reviews"]

    refinements = refine_solutions(problem, roles, initial_solutions, peer_reviews)
    judge_decision = judge_final_answer(problem, roles, initial_solutions, peer_reviews, refinements)
    counterfactual_verdicts = run_counterfactual_judging(
        problem, roles, initial_solutions, peer_reviews, refinements
    )
    counterfactual_judging = build_verdict_bundle(
        problem, roles, judge_decision, counterfactual_verdicts
    )

    updated = dict(run)
    updated["refinements"] = refinements
    updated["judge_decision"] = judge_decision
    updated["counterfactual_judging"] = counterfactual_judging
    updated["winner"] = judge_decision.get("winner")
    updated["final_answer"] = judge_decision.get("final_answer")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RESULTS_DIR / "debate_runs.json")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "debate_runs_v2.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    runs: List[Dict[str, Any]] = json.loads(args.input.read_text(encoding="utf-8"))
    if args.limit is not None:
        runs = runs[: args.limit]

    updated_runs: List[Dict[str, Any]] = []
    for index, run in enumerate(runs, start=1):
        print("=" * 80)
        print(f"Re-running Stage 3+ for problem {index}/{len(runs)}: {run.get('problem_id')}")
        updated_runs.append(rerun_one(run))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(updated_runs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved result for problem: {run.get('problem_id')}")

    print("=" * 80)
    print(f"Done. Wrote {len(updated_runs)} runs to {args.output}")


if __name__ == "__main__":
    main()
