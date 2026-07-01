# existentiAIsm Final Project Checklist

## Project Direction

This is not the default assignment implementation anymore. We modified the required multi-LLM collaborative debate system into a philosopher-inspired debate system.

The final version should still satisfy the assignment workflow:

- 3 independent solvers
- 1 final judge
- peer review between solvers
- refinement based on critiques
- final judgment
- 25-problem dataset
- baseline comparison
- metrics
- plots
- notebook
- README/run instructions

Recommended final role mapping:

- Solver 1: Kant - deontological reasoning
- Solver 2: Mill - utilitarian reasoning
- Solver 3: Nietzsche - critique of values and assumptions
- Judge: Camus - final evaluator focused on clarity, limits, and human consequences

Socrates can remain as UI flavor, but the graded pipeline should use 3 solvers + 1 judge.

## Current Status

Estimated completion: 30-35%.

Strongest part:

- Agon frontend
- visual concept
- local web server
- basic OpenAI API connection

Weakest part:

- required pipeline stages
- real 25-problem dataset
- evaluation metrics
- generated plots
- notebook analysis

## Already Done

- [x] Created project repository structure.
- [x] Created philosopher-inspired concept.
- [x] Added philosopher agent files:
  - [x] `agents/kant.py`
  - [x] `agents/mill.py`
  - [x] `agents/nietzsche.py`
  - [x] `agents/camus.py`
- [x] Built Agon frontend in `website/index.html`.
- [x] Matched the standalone Agon visual direction.
- [x] Kept Arena design.
- [x] Restored Disputants section closer to `Agon - Standalone.html`.
- [x] Restored Record section closer to `Agon - Standalone.html`.
- [x] Added local Python web server in `web_app.py`.
- [x] Added `/api/debate` endpoint.
- [x] Connected frontend to backend API.
- [x] Kept API key server-side using `.env`.
- [x] Added basic OpenAI call path.
- [x] Added basic debate flow in the web app:
  - [x] opening statements
  - [x] rebuttals
  - [x] final verdict
- [x] Added README setup/run instructions.
- [x] Created scaffold files for pipeline stages.
- [x] Created scaffold files for evaluation.
- [x] Created placeholder `data/problems.json`.

## Still Required

### Dataset

- [x] Replace placeholder `data/problems.json`.
- [x] Create 25 challenging problems.
- [ ] Include multiple categories, for example:
  - [x] mathematical/logical reasoning
  - [x] physics/scientific reasoning
  - [x] logic puzzles/constraint satisfaction
  - [x] strategic game theory
  - [x] philosophical/ethical reasoning, if kept relevant and verifiable
- [ ] Each problem must include:
  - [x] id
  - [x] category
  - [x] difficulty
  - [x] question
  - [x] expected answer
  - [x] grading notes
- [x] Make sure every expected answer is verifiable.

### Pipeline

- [ ] Implement Stage 0: role self-assessment.
- [ ] Implement Stage 0.5: deterministic role assignment.
- [ ] Implement Stage 1: independent solution generation.
- [ ] Implement Stage 2: peer review.
- [ ] Implement Stage 3: refinement based on feedback.
- [ ] Implement Stage 4: final judgment.
- [ ] Update `main.py` to run the full pipeline.
- [ ] Save full debate outputs to `results/`.
- [ ] Make outputs structured JSON.

### Required Workflow Details

- [ ] Each solver produces an independent solution.
- [ ] Solvers do not communicate during Stage 1.
- [ ] Each solver reviews the other two solvers.
- [ ] Each solver receives two reviews.
- [ ] Each solver explicitly addresses critiques.
- [ ] Each solver produces a refined answer.
- [ ] Judge receives:
  - [ ] original solutions
  - [ ] peer reviews
  - [ ] refined solutions
- [ ] Judge picks a winner.
- [ ] Final answer is copied from the winner.

### Evaluation

- [x] Implement single-LLM baseline.
- [x] Implement simple voting baseline.
- [x] Implement full debate evaluation.
- [x] Implement metrics:
  - [x] overall accuracy
  - [x] improvement rate
  - [x] consensus rate
  - [x] judge accuracy
- [x] Save evaluation results as JSON/CSV.
- [x] Generate required plots.
- [x] Add plots to `results/plots/`.

### Notebook

- [x] Add or complete analysis notebook.
- [x] Load final results.
- [x] Show metric tables.
- [x] Show generated plots.
- [x] Explain where debate improved or failed.
- [x] Compare against baselines.

### README

- [ ] Explain philosopher modification clearly.
- [ ] Explain final role mapping.
- [ ] Add setup instructions.
- [ ] Add `.env` instructions.
- [ ] Add command to run web app.
- [ ] Add command to run full pipeline.
- [ ] Add command to generate metrics/plots.
- [ ] Add project structure.
- [ ] Add example output.

### GitHub / Submission

- [ ] Push to GitHub.
- [ ] Make sure all three people contribute commits.
- [ ] Avoid one-person/one-commit submission.
- [ ] Include notebooks.
- [ ] Include README.
- [ ] Include generated plots.
- [ ] Include run instructions.

## What We Can Advance

Target completion if we focus correctly: 80-90%.

Priority order:

1. Implement the required pipeline.
2. Create the 25-problem dataset.
3. Implement evaluation and plots.
4. Add notebook analysis.
5. Polish README.
6. Improve frontend only after required functionality is complete.

Avoid spending more time on UI until the required backend/evaluation work is complete.

## Three-Person Work Split

### Person 1: Pipeline / Backend

Main responsibility: make the assignment workflow real.

Tasks:

- [ ] Implement `pipeline/stage0_assess.py`.
- [ ] Implement `pipeline/stage0_5_assign.py`.
- [ ] Implement `pipeline/stage1_solve.py`.
- [ ] Implement `pipeline/stage2_review.py`.
- [ ] Implement `pipeline/stage3_refine.py`.
- [ ] Implement `pipeline/stage4_judge.py`.
- [ ] Update `main.py`.
- [ ] Save complete runs to `results/debate_runs.json`.
- [ ] Ensure JSON outputs are consistent and reusable by evaluation code.

Estimated project weight: 40%.

### Person 2: Dataset / Evaluation

Main responsibility: make the project measurable.

Tasks:

- [x] Build `data/problems.json` with 25 real problems.
- [x] Add expected answers and grading notes.
- [x] Implement `evaluation/baseline.py`.
- [x] Implement `evaluation/metrics.py`.
- [x] Implement `evaluation/plots.py`.
- [x] Generate plots into `results/plots/`.
- [x] Create/update notebook analysis.
- [x] Compare full debate system to baselines.

Estimated project weight: 35%.

### Person 3: Agents / Frontend / Documentation

Main responsibility: keep the philosopher modification coherent and make the project demo-ready.

Tasks:

- [ ] Clean and strengthen philosopher prompts.
- [ ] Align real backend roles to 3 solvers + 1 judge.
- [ ] Keep Agon web app working.
- [ ] Make web app display real backend outputs cleanly.
- [ ] Optionally load saved debates into Record section.
- [ ] Expand README.
- [ ] Prepare presentation explanation.
- [ ] Explain why the philosopher framing still satisfies the original assignment.

Estimated project weight: 25%.

## Implementation Recommendation

Use one OpenAI model for all four roles if needed, with different system prompts.

This is acceptable according to the requirements because the assignment allows using the same model for all four roles with different parameters/system prompts.

Suggested `.env`:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5-mini
```

Suggested final command flow:

```bash
pip install -r requirements.txt
python3 main.py
python3 web_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Final Submission Risk

High-risk missing items:

- [ ] 25 real problems.
- [ ] Real pipeline stages.
- [ ] Evaluation metrics.
- [ ] Generated plots.
- [ ] Notebook.

These are required by the final project document and should be prioritized before any additional design work.
