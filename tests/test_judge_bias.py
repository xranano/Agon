"""Deterministic unit tests for the Judge-Bias Analysis (no API calls)."""

import unittest

from evaluation.judge_bias import (
    fleiss_kappa,
    home_tradition_win_rate,
    judge_agreement_matrix,
    rank_distance,
    tradition_keywords,
)


def _verdict(judge_agent_id, winner_role, rankings, reasoning=""):
    return {
        "judge_agent_id": judge_agent_id,
        "judge_agent_name": "x",
        "winner": winner_role,
        "rankings": rankings,
        "final_answer": "x",
        "confidence": 0.8,
        "reasoning": reasoning,
    }


def _run(solver_agent_ids, winners_by_judge):
    solver_roles = {f"solver_{i + 1}": aid for i, aid in enumerate(solver_agent_ids)}
    role_by_agent = {aid: role for role, aid in solver_roles.items()}
    verdicts = {}
    for judge_agent_id, winner_agent_id in winners_by_judge.items():
        winner_role = role_by_agent[winner_agent_id]
        other_roles = [r for r in solver_roles if r != winner_role]
        verdicts[judge_agent_id] = _verdict(judge_agent_id, winner_role, [winner_role] + other_roles)
    return {
        "assigned_roles": {"judge": next(iter(winners_by_judge)), "solver_roles": solver_roles},
        "counterfactual_judging": {"verdicts": verdicts},
    }


class RankDistanceTests(unittest.TestCase):
    def test_identical_rankings_is_zero(self):
        self.assertEqual(rank_distance(["solver_1", "solver_2", "solver_3"], ["solver_1", "solver_2", "solver_3"]), 0)

    def test_reversed_rankings_is_max(self):
        self.assertEqual(rank_distance(["solver_1", "solver_2", "solver_3"], ["solver_3", "solver_2", "solver_1"]), 4)

    def test_adjacent_swap(self):
        self.assertEqual(rank_distance(["solver_1", "solver_2", "solver_3"], ["solver_2", "solver_1", "solver_3"]), 2)


class FleissKappaTests(unittest.TestCase):
    def test_perfect_agreement_is_one(self):
        solvers = ["agent_1", "agent_2", "agent_3"]
        run = _run(solvers, {f"agent_{i}": "agent_1" for i in range(1, 6)})
        problems = [{"id": "p1"}]
        runs = {"p1": run}
        self.assertAlmostEqual(fleiss_kappa(problems, runs), 1.0)

    def test_returns_none_when_no_complete_verdict_sets(self):
        self.assertIsNone(fleiss_kappa([{"id": "p1"}], {"p1": {"counterfactual_judging": {"verdicts": {}}}}))


class HomeTraditionWinRateTests(unittest.TestCase):
    def test_arithmetic_on_small_fixture(self):
        solvers = ["agent_1", "agent_2", "agent_3"]
        # agent_1 (kant) always favors itself across 3 problems where it's a solver.
        run = _run(solvers, {"agent_1": "agent_1", "agent_2": "agent_2", "agent_3": "agent_3", "agent_4": "agent_1", "agent_5": "agent_2"})
        problems = [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
        runs = {"p1": run, "p2": run, "p3": run}
        htwr = home_tradition_win_rate(problems, runs)
        self.assertEqual(htwr["kant"]["home_wins"], 3)
        self.assertEqual(htwr["kant"]["n_eligible"], 3)
        self.assertEqual(htwr["kant"]["htwr"], 1.0)
        # plato/camus are never solvers in this fixture -> not eligible
        self.assertIsNone(htwr["plato"]["htwr"])
        self.assertEqual(htwr["plato"]["n_eligible"], 0)


class JudgeAgreementMatrixTests(unittest.TestCase):
    def test_diagonal_is_one(self):
        solvers = ["agent_1", "agent_2", "agent_3"]
        run = _run(solvers, {f"agent_{i}": "agent_1" for i in range(1, 6)})
        matrix = judge_agreement_matrix([{"id": "p1"}], {"p1": run})["matrix"]
        for i in range(5):
            self.assertEqual(matrix[i][i], 1.0)


class VocabularyOverlapTests(unittest.TestCase):
    def test_tradition_keywords_nonempty_for_all_traditions(self):
        for tradition in ("kant", "nietzsche", "aristotle", "plato", "camus"):
            self.assertTrue(tradition_keywords(tradition))


if __name__ == "__main__":
    unittest.main()
