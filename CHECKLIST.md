# existentiAIsm Checklist — rebuilt from `project-agon.md`

**Due: 3 July 2026, 23:59.** This checklist supersedes the old one, which was written
for an earlier draft (3 fixed solvers, no counterfactual judging, no judge-bias
analysis, STEM-then-philosophy dataset). That draft is now obsolete — the current
spec is `project-agon.md`: 5 philosophers, 3 solvers + 1 judge + 1 sits out per
problem, Stage 4.5 counterfactual judging, and a judge-bias analysis as the
headline finding.

Marks: `[x]` done and verified against the current code, `[~]` partially done /
implemented but not spec-compliant, `[ ]` not started.

---

## Cast

- [x] Five philosopher personas implemented — Kant, Nietzsche, Aristotle, Plato,
      Camus (`pipeline/agent_registry.py`). Old Mill/Socrates-era agent files
      (`agents/*.py`) already deleted.
- [x] One model, five system prompts (`OPENAI_MODEL` in `.env`) — satisfies the
      "one free model for all roles" allowance.

---

## Phase 1: Problem Dataset Construction

- [x] 25 problems rewritten to the new schema (`data/problems.json`) — canonical
      dilemmas removed (verified: `validate_problems.py`'s blocklist scan finds
      zero hits for trolley/footbridge/murderer-at-the-door/Gyges/experience-
      machine/violinist across all 25 questions), category distribution matches
      the required 6/5/5/4/5 exactly across `classical_ethics_and_moral_dilemmas`,
      `political_philosophy_and_justice`, `human_nature_and_the_good_life`,
      `knowledge_truth_and_reality`, `power_society_and_the_individual`.
- [x] Problem JSON schema rework — every problem now has `why_this_works`
      (`position` + `core_reason` for all five philosophers), `expected_conflict`,
      `difficulty_reason`, `annotations` (`annotator_1/2/3`),
      `expected_strongest_tradition`, `label_agreement`.
- [x] **Ground-Truth Labeling Protocol** — done. All 25 problems independently
      labeled by the three team members and inserted into `data/problems.json`.
      All 25 reach the required ≥2/3 majority: 4 unanimous (3/3), 21 at 2/3.
      Raw percent agreement (avg. annotator votes matching the majority) =
      **72.0%**. 6 problems (008, 011, 013, 015, 017, 020) initially came back
      as genuine 3-way splits; per the written protocol these were resolved by
      one annotator revising their label (not an ad-hoc tiebreak rule) into a
      real 2/3 majority — worth noting in the report that 6/25 (24%) needed a
      revision pass. `expected_strongest_tradition` distribution is skewed:
      Aristotle 12/25 (48%), Camus 7/25, Kant 4/25, Nietzsche 1/25, Plato 1/25
      — worth flagging in the report since a trivial "always guess Aristotle"
      baseline would hit 48% accuracy.
- [x] `data/validate_problems.py` — schema + distinctness + blocklist gate,
      implemented and verified. Enforces all six spec requirements: required
      fields/enums/unique ids, `why_this_works` completeness, distinctness
      (difflib similarity on `position`+`core_reason`, ≥0.85 on both flags a
      collapse), `expected_strongest_tradition`/`label_agreement` consistency
      with `annotations`, category counts, and the canonical-dilemma keyword
      blocklist. Stress-tested against 6 synthetic violations (duplicate id,
      distinctness collapse, blocklisted question, wrong category count,
      3-way annotator split, majority mismatch) — all caught correctly, no
      false positives. `python data/validate_problems.py` now passes clean on
      the full, fully-annotated 25-problem dataset (exit 0, "All checks passed").

---

## Phase 2: System Implementation

- [x] **Stage 0 — Role Self-Assessment** (`pipeline/stage0_assess.py`) — each of
      the five philosophers returns Solver/Judge confidence scores.
- [x] **Stage 0.5 — Deterministic Role Assignment** (`pipeline/stage0_5_assign.py`)
      — fixed and verified. Judge is now selected by highest Judge confidence,
      ties broken by smallest Solver–Judge confidence gap then alphabetically;
      the remaining philosopher with the lowest Solver confidence now sits out
      (`sits_out` field added to `AssignedRoles`); auto mode raises if it ever
      produces something other than exactly 3 solvers. Verified with targeted
      unit tests (exact-confidence ties on both the judge and sit-out rules)
      and a live end-to-end smoke test. (Manual "selector" mode, used only by
      the web demo, intentionally keeps its 2–4 solver flexibility — that's a
      separate UI feature, not the graded auto-assignment path.)
- [~] **Stage 1 — Independent Solution Generation** (`pipeline/stage1_solve.py`)
      — solvers reason independently and commit to a position, but the schema
      folds framework/key-considerations/strongest-counterargument into a
      single free-text `solution` field rather than the structured fields shown
      in the spec's Stage 1 JSON example. Functionally close; not a blocker.
- [x] **Stage 2 — Peer Review** (`pipeline/stage2_review.py`) — each solver
      reviews every other solver from its own tradition; 2 strengths/
      weaknesses/errors/suggested-changes; matches spec closely.
- [x] **Stage 3 — Refinement** (`pipeline/stage3_refine.py`) — each solver
      addresses every critique with an explicit `accepted` flag, ≤3 changes;
      matches spec.
- [x] **Stage 4 — Final Judgment** (`pipeline/stage4_judge.py`) — judge receives
      all three stages of material, picks a winner, and now also returns
      `rankings` (ordered list of all solvers, `winner == rankings[0]`) —
      needed for Judge Reliability and the Camus-Deviation Score. Verified
      live: rankings well-formed, winner matched rankings[0].
- [x] **Stage 4.5 — Counterfactual Judging** — implemented
      (`pipeline/stage4_5_counterfactual.py`) and verified live. The judge
      prompt was refactored into a shared `judge_as()` in `stage4_judge.py` so
      Stage 4 and Stage 4.5 are guaranteed to use the identical prompt;
      `run_counterfactual_judging` re-judges the frozen bundle with the 4
      non-assigned philosophers (only 4 new API calls — the assigned judge's
      Stage 4 result is reused, not re-run), and `build_verdict_bundle`
      combines those into the full 5-verdict-per-problem structure. Wired into
      `main.py` behind `run_counterfactual` (default on for `python main.py`,
      `--skip-counterfactual` flag for cheap dev runs) and explicitly turned
      **off** in `web_app.py` per the spec ("evaluation-only, not part of the
      user-facing pipeline"). Live smoke test confirmed: 5 well-formed
      verdicts keyed by all 5 agent ids, `judge_agent_id` matches each dict
      key, `rankings` contains exactly the 3 solver roles with
      `winner == rankings[0]`, and the reused assigned-judge entry is byte-
      identical to the real Stage 4 decision. Bonus finding from the smoke
      test itself: Kant-as-judge was the only one of the 5 judges to pick
      Kant's own submission as winner while the other 4 independently agreed
      on a different solver — exactly the self-preference signal HTWR is
      meant to catch.
- [~] Persona/stage-instruction separation principle — `agent_registry.py`
      holds reusable persona metadata (name, framework, style) that every stage
      prompt pulls from, which satisfies the spirit of the principle. No
      dedicated `agents/personas.py` module exists yet, which the companion
      chatbot will need to import from.

---

## Phase 3: Evaluation and Analysis

**Updated 2026-07-02/03: the full real pipeline (25 problems, incl. Stage 4.5
counterfactual judging, ~550 API calls) has been run and every module below
executed against it (`python3 -m evaluation.metrics` then
`python3 -m evaluation.plots`) — this is no longer aspirational, the numbers
below are real. Actual result files: `results/debate_runs.json`,
`results/evaluation_summary.json`, `results/*_rows.json`, `results/plots/*.png`.**

- [x] Single-LLM baseline (`evaluation/baseline.py`) — `single_agent_baseline`:
      8% (2/25).
- [x] Simple voting baseline — majority vote over Stage 1 answers by
      near-duplicate text clustering, falling back to highest self-reported
      confidence when no majority forms; fallback fired **84%** of the time
      (`baselines.fallback_rate`), consistent with persona distinctness being
      a design goal. `majority_vote_baseline`: 20% (5/25).
- [x] Full-debate system as third comparison point — `full_debate`: **40%**
      (10/25). Clean escalating story: single-agent 8% → majority-vote 20% →
      full-debate 40%.
- [x] **Verdict Accuracy** — reworked; grades the judge's winning solver's
      tradition against `expected_strongest_tradition` (deterministic match,
      no LLM grading needed). Overall 40% (10/25), reported per-category with
      `mean_label_agreement` alongside every figure
      (`verdict_accuracy_rows.json`).
- [x] **Improvement Rate** — order-bias controlled: every pairwise
      Stage-1-vs-Stage-3 comparison (scoped to the judge's winning solver) runs
      twice with positions swapped; a side only "wins" if it wins both
      orderings, else recorded as a tie. Result: **88% improved**, 4%
      regressed, 8% tie, **92% position-consistency rate**
      (`improvement_rate_rows.json`).
- [x] **Persona Distinctness** — reframed correctly: `distinct_rate` where LOW
      is the success condition (persona collapse sanity check), broken down by
      difficulty and category. Result: only **32% distinct** (68% of problems
      converged to the same practical verdict across traditions) — a real,
      somewhat concerning finding worth stating honestly in the report rather
      than hiding (spec's implicit target was >90% distinct).
- [x] **Judge Reliability** metric — implemented
      (`judge_reliability_summary`): accuracy on "clearly opposed" problems
      (non-converged per persona-distinctness pass) = 50% (4/8 opposed
      problems), `rankings_consistency_rate` (winner == rankings[0]) = 100%.
- [x] **Fidelity rubric scoring** (`evaluation/fidelity_rubrics.py`) —
      implemented: per-tradition binary checklists (3–4 criteria each, copied
      verbatim from `project-agon.md`), persona-free LLM grader scores every
      Stage 1 and Stage 3 solution, aggregated to a per-tradition
      stage1/stage3/delta score. Feeds `plot_fidelity_delta`.
- [x] **Position Change** per philosopher (`position_change_by_tradition`) —
      accepted vs. rejected critique counts + acceptance rate per tradition,
      computed directly from Stage 3 `accepted` flags.
- [x] **Critique Quality** proxies (`critique_quality_summary`) — (a)
      acceptance rate by reviewer tradition via fuzzy critique-to-review
      attribution, (b) lexical near-duplicate boilerplate flagging across all
      reviews. (c) team spot-check sample export
      (`sample_reviews_for_spot_check`) still needs a human pass before the
      report is written.
- [x] **Judge-Bias Analysis** (`evaluation/judge_bias.py`, 318 lines) — fully
      implemented and run on the real 125 counterfactual verdicts:
  - [x] Home-Tradition Win Rate (HTWR) per judge + binomial test vs. 1/3. **The
        headline finding**: Aristotle-as-judge picks Aristotle as winner
        **87%** of the time (20/23 eligible, p≈1.6×10⁻⁷, highly significant).
        Kant self-favors too (71%, 5/7, p=0.045, significant). Nietzsche
        (4%), Plato (32%), Camus (33%) show no significant self-preference.
  - [x] Home-Tradition Advantage (HTA), the causal counterfactual version —
        `home_tradition_advantage` implemented, reads
        `run["counterfactual_judging"]["verdicts"]`.
  - [x] 5×5 Judge-Verdict Agreement Matrix + Fleiss' kappa — implemented,
        hand-rolled (no statsmodels dependency). Result: **κ = 0.57**
        (moderate agreement across the 5 judges).
  - [x] Camus-Deviation Score per judge — implemented (Spearman-footrule rank
        distance). Result: Kant/Nietzsche ≈0.8, Plato ≈0.72, Aristotle ≈0.64
        (out of max 4).
  - [x] Fairness-of-Reasoning proxy (per-solver reference counts, vocabulary
        overlap with own tradition's rubric keywords) — implemented
        (`fairness_of_reasoning`).
- [x] Inter-annotator agreement reported alongside every accuracy figure —
      wired into `metrics.py`'s `verdict_accuracy_summary` (`mean_label_agreement`
      per category) and top-level `label_agreement` summary (72.0% overall).
- [x] **Plots** (`evaluation/plots.py`) — all 8 required plots implemented and
      regenerated from the real run (matplotlib path, no SVG fallback needed):
  1. [x] `verdict_accuracy_by_category.png`
  2. [x] `improvement_rate.png` (with tie band)
  3. [x] `persona_distinctness_by_difficulty.png`
  4. [x] `baseline_comparison.png` (system vs. two baselines)
  5. [x] `fidelity_delta.png` (per philosopher per stage)
  6. [x] `judge_bias_heatmap.png` (5 judges × winning tradition, from 125
         counterfactual verdicts)
  7. [x] `htwr_per_judge.png` + `judge_agreement_matrix.png` (HTWR vs. 1/3
         line, and the 5×5 judge-agreement matrix, split into two files)
  8. [x] `camus_deviation.png`
- [x] Results-saving mechanism and `notebooks/analysis.ipynb` exist and pick
      up the regenerated real data (`results/evaluation_summary.json` and the
      `*_rows.json` files are fresh as of this run).

**Not yet done in Phase 3**: (c) above — the human spot-check sample for
Critique Quality — and a written analysis/report synthesizing these numbers
(the checklist tracks code + generated artifacts, not the prose report itself).

---

## Companion Feature: Talk to a Philosopher (Day 2)

- [ ] `chat/chatbot.py` reusing persona objects — not implemented.
- [ ] Single-philosopher conversation loop with message history — not
      implemented.
- [ ] (Stretch, only after the above is solid) multi-philosopher room — not
      implemented.

This is explicitly the lowest-priority item in the spec ("Day 2") — do not start
it before Phase 1–3 blockers above are closed, given the deadline.

---

## Deliverables / Repo Structure

- [x] `data/`, `pipeline/`, `evaluation/`, `website/`, `notebooks/`, `main.py`,
      `config.py`, `requirements.txt`, `README.md` all present and match the
      suggested layout.
- [x] `tests/` present (`tests/test_metrics.py`, currently untracked).
- [ ] `agents/personas.py` — not present as its own module; persona data
      currently lives only in `pipeline/agent_registry.py`. Fine for the debate
      pipeline, but the chatbot needs a persona module it can import without
      pulling in pipeline stage logic — worth factoring out before Day 2 work.
- [ ] `chat/` directory — not present.
- [x] `data/validate_problems.py` — present and verified (see Phase 1).
- [x] `evaluation/judge_bias.py` (318 lines), `evaluation/fidelity_rubrics.py`
      (159 lines) — both present, implemented, and run against real data (see
      Phase 3).
- [x] `pipeline/stage4_5_counterfactual.py` — present (see Phase 2).

---

## Submission

- [ ] Push to GitHub — local branch is currently 2 commits ahead of
      `origin/main`, not yet pushed. Nothing from this session's real pipeline
      run/evaluation rewrite is committed yet either.
- [ ] Confirm commit history shows all three team members contributing
      (rebalance if lopsided — currently Luka ~13, Anano ~5, nino 1).
- [ ] README rewrite — current README already covers the 5-philosopher /
      dynamic-assignment framing and the new dataset, but still has **no
      mention of Stage 4.5 counterfactual judging or the judge-bias finding**
      (verified: zero hits for "counterfactual"/"judge-bias"/"HTWR"/"sit_out"
      in `README.md`). Needs a section on the judge-bias headline result now
      that real numbers exist (Aristotle 87% self-preference, p≈1.6e-7).
- [ ] Regenerate and commit final `results/` and `results/plots/` — **the real
      run is done** (25/25 problems, all evaluation modules, all 9 plot files
      generated 2026-07-02/03). What remains is committing these artifacts,
      ideally right before submission so they reflect final code.

---

## Suggested priority order given ~1 day left

1. ~~Fix Stage 0.5~~ — done. ~~Implement Stage 4.5~~ — done. ~~Rewrite
   dataset~~ — done. ~~Build `validate_problems.py`~~ — done. ~~Run labeling
   protocol~~ — done. ~~Implement `judge_bias.py`/`fidelity_rubrics.py`,
   rework `metrics.py`~~ — done. ~~Rebuild the 8 required plots~~ — done.
   ~~Run the full real pipeline (25 problems) and full evaluation~~ — **done
   2026-07-02/03**, results are credible (40% full-debate accuracy vs 20%/8%
   baselines; Aristotle judge self-preference p≈1.6e-7).
2. **Remaining critical path**: README judge-bias/Stage-4.5 section →
   human spot-check sample for Critique Quality (optional, nice-to-have) →
   commit rebalancing across the 3 teammates → commit results/plots → push.

Chatbot (Day 2) only after all of the above, time permitting — correctly still
untouched.