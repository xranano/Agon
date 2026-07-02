"""Deterministic unit tests for fidelity rubric scoring helpers (no API calls).

Does NOT test `score_fidelity` itself -- that calls the API.
"""

import unittest

from evaluation.fidelity_rubrics import RUBRICS, FidelityCriterion, FidelityScore, fidelity_numeric_score


class RubricsSanityTests(unittest.TestCase):
    def test_all_five_traditions_present(self):
        self.assertEqual(set(RUBRICS.keys()), {"kant", "nietzsche", "aristotle", "plato", "camus"})

    def test_criteria_counts_match_spec(self):
        self.assertEqual(len(RUBRICS["kant"]), 4)
        self.assertEqual(len(RUBRICS["nietzsche"]), 4)
        self.assertEqual(len(RUBRICS["aristotle"]), 3)
        self.assertEqual(len(RUBRICS["plato"]), 3)
        self.assertEqual(len(RUBRICS["camus"]), 3)


class FidelityNumericScoreTests(unittest.TestCase):
    def test_all_true_is_one(self):
        score = FidelityScore(
            tradition="kant",
            criteria_results=[FidelityCriterion(criterion="a", met=True, evidence="") for _ in range(4)],
        )
        self.assertEqual(fidelity_numeric_score(score), 1.0)

    def test_mixed_is_averaged(self):
        score = FidelityScore(
            tradition="kant",
            criteria_results=[
                FidelityCriterion(criterion="a", met=True, evidence=""),
                FidelityCriterion(criterion="b", met=False, evidence=""),
            ],
        )
        self.assertEqual(fidelity_numeric_score(score), 0.5)

    def test_empty_criteria_is_zero(self):
        score = FidelityScore(tradition="kant", criteria_results=[])
        self.assertEqual(fidelity_numeric_score(score), 0.0)


if __name__ == "__main__":
    unittest.main()
