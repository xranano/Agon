# existentiAIsm

Structured multi-agent philosophical debate system.

This project modifies the default multi-LLM debate assignment by using five
philosopher-inspired agents (instead of a fixed cast of solvers) and staging
genuine philosophical conflict rather than a neutral checklist review:

1. Role self-assessment — all five philosophers self-rate Solver vs. Judge confidence.
2. Deterministic role assignment — one Judge, three Solvers, **one sits out**,
   chosen entirely from those self-assessments (no philosopher is pre-weighted
   toward Judge).
3. Independent solver responses (no cross-talk).
4. Structured peer review, each solver critiquing from its own tradition.
5. Refinement based on critiques (accept-and-revise or defend-and-hold).
6. Final judge decision, with full rankings.
7. **Counterfactual judging** — the identical frozen solution bundle is
   additionally judged by all four non-assigned philosophers, so every problem
   yields 5 verdicts on the same inputs with judge identity as the only
   variable.
8. Evaluation against baselines, fidelity/critique-quality metrics, and a
   **judge-bias analysis** — see [Results](#results-real-data-not-simulated) below.

## Models

Following the assignment's allowance to "use a free model for all four roles ...
with different parameters/system prompts", all agents run on **one OpenAI model**
(`OPENAI_MODEL`, default `gpt-5-mini`) driven by different philosopher personas
and role prompts. There are five personas — Kant (deontology), Nietzsche (master
morality), Aristotle (virtue ethics), Plato (idealism), Camus (absurdism) — and the
solver/judge/sit-out roles are assigned **dynamically per problem** from Stage-0
self-assessment, not fixed in advance. That's deliberate: it makes judge
neutrality a variable the evaluation can actually measure (see Results).

## Dataset

`data/problems.json` holds 25 **gradeable philosophical problems** across five categories
(applied-ethics dilemmas, history of philosophy, metaethics/value theory, political/social
philosophy, and existential/mind). Each problem has a defensible expected position plus the
required considerations a strong answer must engage — so answers are open-ended in wording
but not in quality (a one-sided, incoherent, or philosopher-misstating answer is graded
incorrect). This is where the Kant/Nietzsche/Aristotle/Plato/Camus personas genuinely
diverge and debate can improve the outcome.

> An earlier STEM version of the dataset (math/physics/logic/game-theory) is kept at
> `data/problems_stem_archive.json`, with its evaluation in `results/stem_baseline/`.
> On that set the model scored 100% across all systems (too easy to differentiate debate),
> which motivated the pivot to philosophical problems.

## Evaluation is real, not simulated

`python main.py` runs the full debate (plus Stage 4.5 counterfactual judging) on
all 25 problems and writes `results/debate_runs.json` — every downstream number
is derived from that one real run, never hardcoded or copied from ground truth.
`single_agent_baseline` = a solver's pre-debate answer's tradition,
`majority_vote_baseline` = the majority tradition over the three pre-debate
answers (falling back to highest self-reported confidence when no majority
forms — the common case, since personas are designed to stay distinct),
`full_debate` = the judge's winning tradition after peer review and
refinement. Accuracy is a deterministic match against each problem's
`expected_strongest_tradition`, a proxy ground truth produced by an
independent three-annotator labeling protocol (documented in
`data/problems.json`'s `annotations` field; 72.0% raw inter-annotator
agreement, reported alongside every accuracy figure).

### Results (real data, not simulated)

From the full 25-problem run (`results/evaluation_summary.json`):

| System | Accuracy |
|---|---|
| Single-agent baseline | 8% (2/25) |
| Majority-vote baseline | 20% (5/25) |
| **Full debate** | **40% (10/25)** |

- **Improvement rate**: 88% of refinements improved on the initial solution
  (order-bias controlled — every comparison run twice with positions swapped;
  92% position-consistency rate).
- **Persona distinctness**: only 32% of problems stayed distinct across all
  three solvers (68% converged on the same practical verdict despite arguing
  from incompatible traditions) — a real finding about persona strength under
  gpt-5-mini, reported honestly rather than smoothed over.
- **Judge-Bias Analysis — the headline finding.** Because Stage 0.5 assigns
  Judge dynamically and Stage 4.5 has every philosopher counterfactually judge
  the identical solution bundle, judge identity is causally isolated from
  argument quality. Result: **Aristotle-as-judge picks Aristotle as the
  winner 87% of the time** (20/23 eligible problems, binomial p≈1.6×10⁻⁷
  against the 1/3 chance baseline) — strong, statistically significant
  self-preference. Kant shows the same pattern more mildly (71%, p=0.045).
  Nietzsche (4%), Plato (32%), and Camus (33%) show no significant
  self-preference. Fleiss' κ across the 5 judges = 0.57 (moderate agreement) —
  low enough to confirm that judge identity, not argument quality alone,
  measurably shapes outcomes. See `results/plots/judge_bias_heatmap.png`,
  `htwr_per_judge.png`, `judge_agreement_matrix.png`, and
  `camus_deviation.png`.

## Project Structure

```text
existentiAIsm/
  data/
    problems.json           # 25 problems, incl. annotations + expected_strongest_tradition
    validate_problems.py    # schema + distinctness + canonical-dilemma blocklist gate
    problems_stem_archive.json
  pipeline/
    agent_registry.py           # the 5 philosopher personas (Kant, Nietzsche, Aristotle, Plato, Camus)
    llm_client.py               # OpenAI structured-output client (retries + backoff)
    schemas.py                  # Pydantic schemas for every stage
    stage0_assess.py
    stage0_5_assign.py          # judge/solver/sit-out assignment from self-assessment
    stage1_solve.py
    stage2_review.py
    stage3_refine.py
    stage4_judge.py
    stage4_5_counterfactual.py  # all 5 philosophers judge the identical frozen bundle
  evaluation/
    metrics.py            # verdict accuracy, improvement rate, persona distinctness, judge reliability
    baseline.py            # single-agent / majority-vote / full-debate comparison
    fidelity_rubrics.py    # per-tradition binary rubric scoring (Stage 1 vs Stage 3)
    judge_bias.py           # HTWR, HTA, agreement matrix + Fleiss' kappa, Camus-deviation
    plots.py                 # all 8 required plots
    llm_cache.py              # caches LLM-grader calls so re-running eval never re-queries
  website/
    index.html
  notebooks/
    analysis.ipynb
  results/
    debate_runs.json
    evaluation_summary.json
    plots/
  tests/
  main.py
  config.py
  requirements.txt
```

## Team Split

Person 1: Pipeline
- Stage 0 role assessment
- Stage 0.5 role assignment
- Stage 1 independent solving
- Stage 2 peer review
- Stage 3 refinement
- Stage 4 judging

Person 2: Data and Evaluation
- 25-problem dataset
- Metrics
- Baselines
- Plots
- Analysis notebook

Person 3: Agents and Frontend
- Philosopher prompts
- Base LLM wrapper
- Main orchestration
- Web interface
- README and run instructions

## Setup

Copy the example env file and add your key (see `.env.example`):

```bash
cp .env.example .env
# then edit .env and set OPENAI_API_KEY
```

`.env`:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the full experiment

```bash
# 1. Validate the dataset (schema, distinctness, blocklist, labeling consistency)
python data/validate_problems.py

# 2. Run the debate + Stage 4.5 counterfactual judging on all 25 problems
#    (~550 API calls; saves after every problem so a rate limit never costs a run)
python main.py
# add --skip-counterfactual for a cheap dev run without the 4 extra judges/problem

# 3. Compute every metric (verdict accuracy, improvement rate, persona
#    distinctness, judge reliability, fidelity, position change, critique
#    quality, judge-bias analysis) -> results/evaluation_summary.json + rows
python -m evaluation.metrics

# 4. Generate all 8 required plots -> results/plots/*.png
python -m evaluation.plots
```

Then open `notebooks/analysis.ipynb` for the metric tables, plots, and baseline
comparison.

Generated artifacts:

- `results/debate_runs.json` — full per-problem debate transcripts (all 5.5
  stages, including all 5 counterfactual verdicts per problem).
- `results/evaluation_summary.json` — every metric in [Results](#results-real-data-not-simulated):
  verdict accuracy, improvement rate, persona distinctness, judge reliability,
  fidelity, position change, critique quality, and the full judge-bias analysis.
- `results/{verdict_accuracy,persona_distinctness,improvement_rate,baseline}_rows.json`
  — per-problem rows behind each summary metric.
- `results/plots/*.png` — the 8 required plots (verdict accuracy by category,
  improvement rate, persona distinctness by difficulty, baseline comparison,
  fidelity delta, judge-bias heatmap, HTWR + judge-agreement matrix, and
  Camus-deviation).

## Web app (demo)

```bash
python web_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

The debate UI calls `/api/debate` on the local Python server. Keep `OPENAI_API_KEY`
in `.env`; do not put API keys in `website/index.html`.
