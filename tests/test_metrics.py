"""Deterministic unit tests for evaluation helpers (no API calls).

Run:  python -m unittest discover -s tests   (from the repo root)
"""

import unittest

from evaluation.metrics import (
    attribute_changes_to_reviewers,
    boilerplate_flags,
    final_debate_answer,
    initial_answers,
    judge_tradition,
    majority_answer,
    normalize_text,
    position_change_by_tradition,
    rankings_consistency_rate,
    refined_answers,
    solver_tradition,
    winner_tradition,
)


# A synthetic debate run with the same shape main.py writes to debate_runs.json.
# agent_2=Nietzsche, agent_3=Aristotle, agent_4=Plato, agent_5=Camus.
SYNTHETIC_RUN = {
    "problem_id": "prob_x",
    "assigned_roles": {
        "judge": "agent_5",
        "solver_roles": {"solver_1": "agent_2", "solver_2": "agent_3", "solver_3": "agent_4"},
    },
    "initial_solutions": {
        "solver_1": {"answer": "Pull the lever."},
        "solver_2": {"answer": "Do not pull the lever."},
        "solver_3": {"answer": "Pull the lever."},
    },
    "refinements": {
        "solver_1": {"refined_answer": "Pull the lever."},
        "solver_2": {"refined_answer": "Pull the lever."},
        "solver_3": {"refined_answer": "Pull the lever."},
    },
    "judge_decision": {"winner": "solver_1", "rankings": ["solver_1", "solver_2", "solver_3"], "final_answer": "Pull the lever."},
}


class TextHelpers(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("$66.00!"), "66 00")
        self.assertEqual(normalize_text("  Pull  the LEVER "), "pull the lever")

    def test_majority_answer_clear(self):
        answers = ["Pull the lever.", "Do not pull.", "Pull the lever."]
        self.assertEqual(majority_answer(answers), "Pull the lever.")

    def test_majority_answer_tie_keeps_first(self):
        answers = ["A", "B"]
        self.assertEqual(majority_answer(answers), "A")

    def test_majority_answer_empty(self):
        self.assertEqual(majority_answer([]), "")


class RunExtraction(unittest.TestCase):
    def test_initial_answers_ordered(self):
        self.assertEqual(
            initial_answers(SYNTHETIC_RUN),
            ["Pull the lever.", "Do not pull the lever.", "Pull the lever."],
        )

    def test_refined_answers(self):
        self.assertEqual(refined_answers(SYNTHETIC_RUN), ["Pull the lever."] * 3)

    def test_final_debate_answer(self):
        self.assertEqual(final_debate_answer(SYNTHETIC_RUN), "Pull the lever.")


class IdentityHelpers(unittest.TestCase):
    def test_solver_tradition(self):
        self.assertEqual(solver_tradition(SYNTHETIC_RUN, "solver_1"), "nietzsche")
        self.assertEqual(solver_tradition(SYNTHETIC_RUN, "solver_2"), "aristotle")
        self.assertEqual(solver_tradition(SYNTHETIC_RUN, "solver_3"), "plato")

    def test_judge_tradition(self):
        self.assertEqual(judge_tradition(SYNTHETIC_RUN), "camus")

    def test_winner_tradition(self):
        self.assertEqual(winner_tradition(SYNTHETIC_RUN), "nietzsche")


class JudgeReliabilityTests(unittest.TestCase):
    def test_rankings_consistency_rate_all_consistent(self):
        self.assertEqual(rankings_consistency_rate({"a": SYNTHETIC_RUN}), 1.0)

    def test_rankings_consistency_rate_flags_inconsistency(self):
        inconsistent_run = {
            "judge_decision": {"winner": "solver_2", "rankings": ["solver_1", "solver_2", "solver_3"]},
        }
        runs = {"a": SYNTHETIC_RUN, "b": inconsistent_run}
        self.assertEqual(rankings_consistency_rate(runs), 0.5)

    def test_rankings_consistency_rate_no_rankings_is_zero(self):
        self.assertEqual(rankings_consistency_rate({"a": {"judge_decision": {}}}), 0.0)


class PositionChangeTests(unittest.TestCase):
    def test_position_change_by_tradition_counts(self):
        run = {
            "assigned_roles": {"solver_roles": {"solver_1": "agent_2"}},
            "refinements": {
                "solver_1": {
                    "changes_made": [
                        {"accepted": True},
                        {"accepted": False},
                        {"accepted": True},
                    ]
                }
            },
        }
        result = position_change_by_tradition({"p1": run})
        self.assertEqual(result["nietzsche"], {"accepted": 2, "rejected": 1, "acceptance_rate": 2 / 3})

    def test_position_change_by_tradition_empty_run_is_empty(self):
        self.assertEqual(position_change_by_tradition({}), {})


class CritiqueQualityTests(unittest.TestCase):
    def test_attribute_changes_to_reviewers_matches_best_candidate(self):
        run = {
            "assigned_roles": {"solver_roles": {"solver_1": "agent_2", "solver_2": "agent_3", "solver_3": "agent_4"}},
            "peer_reviews": {
                "solver_1": {
                    "solver_2": {
                        "weaknesses": ["ignores the counterargument about duty"],
                        "suggested_changes": ["address the duty objection"],
                        "errors": [],
                    },
                    "solver_3": {
                        "weaknesses": ["totally unrelated critique about virtue"],
                        "suggested_changes": [],
                        "errors": [],
                    },
                }
            },
            "refinements": {
                "solver_1": {
                    "changes_made": [
                        {"critique": "ignores the counterargument about duty", "accepted": True},
                        {"critique": "something nobody actually said", "accepted": False},
                    ]
                }
            },
        }
        attributions = attribute_changes_to_reviewers(run, "solver_1")
        self.assertEqual(len(attributions), 1)
        self.assertEqual(attributions[0]["reviewer_role"], "solver_2")
        self.assertTrue(attributions[0]["accepted"])

    def test_boilerplate_flags_detects_near_duplicate_reviews(self):
        review_text = {
            "weaknesses": ["ignores the counterargument about duty"],
            "suggested_changes": ["address the duty objection"],
            "errors": [],
        }
        all_reviews = [
            {"problem_id": "p1", "target_role": "solver_1", "reviewer_role": "solver_2", "review": review_text},
            {"problem_id": "p2", "target_role": "solver_1", "reviewer_role": "solver_2", "review": review_text},
            {
                "problem_id": "p3",
                "target_role": "solver_1",
                "reviewer_role": "solver_2",
                "review": {"weaknesses": ["a completely different observation about virtue"], "suggested_changes": [], "errors": []},
            },
        ]
        flags = boilerplate_flags(all_reviews, threshold=0.8)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["similarity"], 1.0)


if __name__ == "__main__":
    unittest.main()
