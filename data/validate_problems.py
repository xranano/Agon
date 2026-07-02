"""Phase 1 dataset-quality gate (project-agon spec).

Enforces, and fails the build (non-zero exit) on any violation:

- required fields present; `category`/`difficulty` from fixed enums; unique `id`
- `why_this_works` has an entry for all five philosophers
- distinctness: no two traditions may share both the same `position` and the
  same `core_reason` on a given problem (near-duplicate, not just exact-string)
- `expected_strongest_tradition` matches the majority of `annotations`, and
  `label_agreement` is at least 2/3
- category counts match the fixed 6/5/5/4/5 distribution
- canonical-dilemma blocklist (trolley / murderer-at-the-door / Gyges-style /
  experience-machine / violinist keywords)

Usage:
    python data/validate_problems.py
    python data/validate_problems.py --allow-incomplete-annotations
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PHILOSOPHERS = ["kant", "nietzsche", "aristotle", "plato", "camus"]
DIFFICULTIES = {"easy", "medium", "hard"}
CATEGORY_COUNTS = {
    "classical_ethics_and_moral_dilemmas": 6,
    "political_philosophy_and_justice": 5,
    "human_nature_and_the_good_life": 5,
    "knowledge_truth_and_reality": 4,
    "power_society_and_the_individual": 5,
}
REQUIRED_FIELDS = {
    "id",
    "category",
    "difficulty",
    "question",
    "why_this_works",
    "expected_conflict",
    "difficulty_reason",
    "annotations",
    "expected_strongest_tradition",
    "label_agreement",
}
ANNOTATOR_KEYS = {"annotator_1", "annotator_2", "annotator_3"}

# Canonical textbook dilemmas the spec explicitly bans, because LLMs recite
# memorized positions on these instead of reasoning from the question itself.
BLOCKLIST_PATTERNS = [
    r"\btrolley\b",
    r"\bfootbridge\b",
    r"\bfat\s*man\b.*\b(track|trolley|bridge)\b",
    r"murderer[\s-]at[\s-]the[\s-]door",
    r"\bgyges\b",
    r"ring\s+of\s+gyges",
    r"experience\s+machine",
    r"\bviolinist\b",
]

DISTINCTNESS_SIMILARITY_THRESHOLD = 0.85


class ValidationError(Exception):
    pass


def load_problems(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    problems = data.get("problems") if isinstance(data, dict) else data
    if not isinstance(problems, list) or not problems:
        raise ValidationError("problems.json must contain a non-empty list of problems.")
    return problems


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def check_schema(problem: dict[str, Any], errors: list[str]) -> None:
    pid = problem.get("id", "<missing id>")
    missing = REQUIRED_FIELDS - set(problem.keys())
    if missing:
        errors.append(f"{pid}: missing required field(s): {sorted(missing)}")
        return  # further checks assume these fields exist

    if not isinstance(problem["id"], str) or not problem["id"]:
        errors.append(f"{pid}: id must be a non-empty string")

    if problem["category"] not in CATEGORY_COUNTS:
        errors.append(
            f"{pid}: category '{problem['category']}' not in fixed enum {sorted(CATEGORY_COUNTS)}"
        )

    if problem["difficulty"] not in DIFFICULTIES:
        errors.append(
            f"{pid}: difficulty '{problem['difficulty']}' not in fixed enum {sorted(DIFFICULTIES)}"
        )

    if not str(problem.get("question", "")).strip():
        errors.append(f"{pid}: question is empty")


def check_unique_ids(problems: list[dict[str, Any]], errors: list[str]) -> None:
    counts = Counter(p.get("id") for p in problems)
    for pid, count in counts.items():
        if count > 1:
            errors.append(f"id '{pid}' is used by {count} problems (must be unique)")


def check_why_this_works(problem: dict[str, Any], errors: list[str]) -> None:
    pid = problem.get("id", "<missing id>")
    wtw = problem.get("why_this_works")
    if not isinstance(wtw, dict):
        errors.append(f"{pid}: why_this_works must be an object")
        return

    missing_philosophers = [ph for ph in PHILOSOPHERS if ph not in wtw]
    if missing_philosophers:
        errors.append(f"{pid}: why_this_works missing philosopher(s): {missing_philosophers}")

    for philosopher in PHILOSOPHERS:
        entry = wtw.get(philosopher)
        if not isinstance(entry, dict) or not entry.get("position") or not entry.get("core_reason"):
            errors.append(
                f"{pid}: why_this_works['{philosopher}'] must have non-empty 'position' and 'core_reason'"
            )


def check_distinctness(problem: dict[str, Any], errors: list[str]) -> None:
    pid = problem.get("id", "<missing id>")
    wtw = problem.get("why_this_works", {})
    present = [ph for ph in PHILOSOPHERS if isinstance(wtw.get(ph), dict)]
    for i, phil_a in enumerate(present):
        for phil_b in present[i + 1 :]:
            entry_a, entry_b = wtw[phil_a], wtw[phil_b]
            position_sim = _similar(entry_a.get("position", ""), entry_b.get("position", ""))
            reason_sim = _similar(entry_a.get("core_reason", ""), entry_b.get("core_reason", ""))
            if (
                position_sim >= DISTINCTNESS_SIMILARITY_THRESHOLD
                and reason_sim >= DISTINCTNESS_SIMILARITY_THRESHOLD
            ):
                errors.append(
                    f"{pid}: distinctness violation -- '{phil_a}' and '{phil_b}' converge on "
                    f"near-identical position (sim={position_sim:.2f}) AND core_reason "
                    f"(sim={reason_sim:.2f}); genuine disagreement requirement fails"
                )


def check_annotations(problem: dict[str, Any], errors: list[str], allow_incomplete: bool) -> None:
    pid = problem.get("id", "<missing id>")
    annotations = problem.get("annotations")
    if not isinstance(annotations, dict) or set(annotations.keys()) != ANNOTATOR_KEYS:
        errors.append(f"{pid}: annotations must have exactly keys {sorted(ANNOTATOR_KEYS)}")
        return

    labels = [str(annotations[key]).strip().lower() for key in sorted(ANNOTATOR_KEYS)]
    if any(not label for label in labels):
        if not allow_incomplete:
            errors.append(f"{pid}: annotations incomplete -- {annotations}")
        return  # nothing further to check until all three are filled in

    label_counts = Counter(labels)
    winner, winner_count = label_counts.most_common(1)[0]
    agreement = f"{winner_count}/3"

    if winner_count < 2:
        errors.append(
            f"{pid}: 3-way annotator split {labels} -- must be revised or replaced per the "
            "labeling protocol, not accepted as-is"
        )
        return

    expected = str(problem.get("expected_strongest_tradition", "")).strip().lower()
    if expected != winner:
        errors.append(
            f"{pid}: expected_strongest_tradition '{expected}' does not match the "
            f"annotation majority '{winner}' ({labels})"
        )

    stated_agreement = str(problem.get("label_agreement", "")).strip()
    if stated_agreement != agreement:
        errors.append(
            f"{pid}: label_agreement '{stated_agreement}' does not match computed "
            f"agreement '{agreement}' from annotations {labels}"
        )


def check_category_counts(problems: list[dict[str, Any]], errors: list[str]) -> None:
    counts = Counter(p.get("category") for p in problems)
    for category, expected_count in CATEGORY_COUNTS.items():
        actual_count = counts.get(category, 0)
        if actual_count != expected_count:
            errors.append(
                f"category '{category}' has {actual_count} problem(s), expected {expected_count}"
            )
    unknown_categories = set(counts) - set(CATEGORY_COUNTS)
    for category in unknown_categories:
        errors.append(f"category '{category}' is not one of the fixed five categories")


def check_blocklist(problem: dict[str, Any], errors: list[str]) -> None:
    pid = problem.get("id", "<missing id>")
    question = _normalize(problem.get("question", ""))
    for pattern in BLOCKLIST_PATTERNS:
        if re.search(pattern, question):
            errors.append(
                f"{pid}: question matches canonical-dilemma blocklist pattern '{pattern}' -- "
                "replace with a concrete, non-canonical scenario"
            )


def validate(problems: list[dict[str, Any]], allow_incomplete_annotations: bool) -> list[str]:
    errors: list[str] = []
    check_unique_ids(problems, errors)
    check_category_counts(problems, errors)
    for problem in problems:
        check_schema(problem, errors)
        check_why_this_works(problem, errors)
        check_distinctness(problem, errors)
        check_annotations(problem, errors, allow_incomplete_annotations)
        check_blocklist(problem, errors)
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate data/problems.json against the project-agon schema.")
    parser.add_argument(
        "--problems",
        type=Path,
        default=Path(__file__).resolve().parent / "problems.json",
        help="Path to problems JSON file.",
    )
    parser.add_argument(
        "--allow-incomplete-annotations",
        action="store_true",
        help="Don't fail on problems whose annotations are still blank (useful mid-labeling); "
        "all other checks still run and still fail the build.",
    )
    args = parser.parse_args()

    try:
        problems = load_problems(args.problems)
    except ValidationError as error:
        print(f"FAIL: {error}")
        sys.exit(1)

    errors = validate(problems, args.allow_incomplete_annotations)

    print(f"Validated {len(problems)} problems from {args.problems}")
    if errors:
        print(f"\n{len(errors)} violation(s):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()
