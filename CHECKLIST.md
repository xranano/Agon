# existentiAIsm Project Checklist

## Current Direction

existentiAIsm is a structured multi-agent debate system with philosopher-inspired roles. The project keeps the assignment-required workflow while presenting the agents through the Agon/philosophical debate concept.

The graded backend now uses five registered agents:

- Kant: deontology and universal law
- Nietzsche: master morality and value critique
- Aristotle: virtue ethics and flourishing
- Plato: idealism and forms
- Camus: absurdist arbiter focused on honesty, courage, and clarity

For each problem, Stage 0 lets the agents self-assess role fit. Stage 0.5 can either auto-assign one judge and three solvers or accept a manual selector choice of one judge and two to four solvers.

## Status Snapshot

Estimated completion: 60-70%.

Strongest parts:

- Agon frontend and local web app
- OpenAI API wiring through server-side `.env`
- Full backend debate pipeline scaffolding and implementation
- Pydantic-validated outputs for role assessment, solving, reviewing, refinement, and judging
- Frontend now calls the real pipeline instead of the old lightweight demo flow

Highest-risk missing parts:

- 25-problem dataset
- Evaluation baselines and metrics
- Generated plots
- Analysis notebook
- README expansion with final run/evaluation instructions
- Persistent web debate history

## What Has Been Done

- [x] Created project repository structure.
- [x] Created philosopher-inspired project concept.
- [x] Added agent modules in `agents/`.
- [x] Built Agon frontend in `website/index.html`.
- [x] Matched the standalone Agon visual direction.
- [x] Kept the Arena, Disputants, and Record sections.
- [x] Added local Python web server in `web_app.py`.
- [x] Added `/api/debate` endpoint.
- [x] Connected frontend to backend API.
- [x] Kept API key server-side through `.env`.
- [x] Added README setup/run basics.
- [x] Added sample problem in `data/problems.json`.
- [x] Added pipeline agent registry in `pipeline/agent_registry.py`.
- [x] Added OpenAI Responses API wrapper in `pipeline/llm_client.py`.
- [x] Added JSON extraction, strict JSON prompting, and retry handling for LLM output.
- [x] Added Pydantic schemas for all pipeline stage outputs in `pipeline/schemas.py`.
- [x] Changed pipeline stages to validate model responses with Pydantic before use.
- [x] Added native OpenAI Pydantic parsing with schema-validation fallback.
- [x] Added role selection modes:
  - [x] `auto`: agents self-assess and deterministic scoring chooses the judge
  - [x] `selector`: the user manually chooses one judge and two to four solvers
- [x] Replaced runtime agent set with Kant, Nietzsche, Aristotle, Plato, and Camus.
- [x] Implemented Stage 0 role self-assessment in `pipeline/stage0_assess.py`.
- [x] Implemented Stage 0.5 deterministic role assignment in `pipeline/stage0_5_assign.py`.
- [x] Implemented Stage 1 independent solver generation in `pipeline/stage1_solve.py`.
- [x] Implemented Stage 2 peer review in `pipeline/stage2_review.py`.
- [x] Implemented Stage 3 critique-based refinement in `pipeline/stage3_refine.py`.
- [x] Implemented Stage 4 final judging in `pipeline/stage4_judge.py`.
- [x] Updated `main.py` to run the full pipeline.
- [x] Added CLI options for problem file, output path, and run limit.
- [x] Save debate runs incrementally to `data/results/debate_runs.json` by default.
- [x] Preserve problem metadata in each saved run.
- [x] Connected `/api/debate` to the real backend pipeline.
- [x] Added frontend role-selection controls for auto vs manual selector assignment.
- [x] Adapted full pipeline runs into frontend transcript turns.
- [x] Made the web server port configurable with `AGON_PORT`.
- [x] Confirmed local `main` is up to date with `origin/main` after pull.

## Remaining Work

### Dataset

- [ ] Expand `data/problems.json` from 1 sample problem to 25 real problems.
- [ ] Include multiple categories:
  - [ ] mathematical/logical reasoning
  - [ ] physics/scientific reasoning
  - [ ] logic puzzles or constraint satisfaction
  - [ ] strategic/game-theory reasoning
  - [ ] philosophical or ethical reasoning only when the answer can be evaluated
- [ ] Ensure every problem has:
  - [ ] `id`
  - [ ] `category`
  - [ ] `difficulty`
  - [ ] `question`
  - [ ] `expected_answer`
  - [ ] `grading_notes`
- [ ] Verify each expected answer is correct and gradeable.

### Pipeline Validation

- [ ] Run `python main.py --limit 1` with a real API key.
- [ ] Inspect `data/results/debate_runs.json` for valid JSON structure.
- [ ] Confirm auto mode includes three solvers and one judge.
- [ ] Confirm selector mode accepts one judge and two to four solvers.
- [ ] Confirm the selected judge cannot also be a selected solver.
- [ ] Confirm Stage 1 solvers do not see each other's answers.
- [ ] Confirm each solver reviews every other selected solver.
- [ ] Confirm each solver receives reviews from every other selected solver.
- [ ] Confirm refinements explicitly respond to received critiques.
- [ ] Confirm the judge receives original solutions, reviews, and refinements.
- [ ] Confirm final answer is copied from or clearly based on the winning refined answer.
- [ ] Add lightweight error handling for partial/failed API runs if needed.

### Evaluation

- [ ] Implement single-LLM baseline in `evaluation/baseline.py`.
- [ ] Implement simple voting baseline in `evaluation/baseline.py`.
- [ ] Implement full debate evaluation.
- [ ] Implement answer grading logic.
- [ ] Implement metrics in `evaluation/metrics.py`:
  - [ ] overall accuracy
  - [ ] improvement rate
  - [ ] consensus rate
  - [ ] judge accuracy
- [ ] Save evaluation results as JSON or CSV.
- [ ] Generate required plots in `evaluation/plots.py`.
- [ ] Save plots under `results/plots/` or document the actual output directory.

### Notebook

- [ ] Add or complete `notebooks/analysis.ipynb`.
- [ ] Load debate runs and baseline results.
- [ ] Show metric tables.
- [ ] Show generated plots.
- [ ] Explain where debate improved over baselines.
- [ ] Explain failure cases and limitations.

### README

- [ ] Explain the philosopher modification clearly.
- [ ] Explain current agent mapping and dynamic judge assignment.
- [ ] Add final project structure.
- [ ] Add `.env` instructions.
- [ ] Add command to run the web app.
- [ ] Add command to run the full pipeline.
- [ ] Add command to run baselines.
- [ ] Add command to generate metrics and plots.
- [ ] Add example output.
- [ ] Explain where generated results are saved.

### Frontend / Demo Polish

- [ ] Keep the existing Agon web app working.
- [x] Decide whether the web app should call the full pipeline or remain a lightweight demo endpoint.
- [x] Make displayed backend outputs readable and consistent.
- [ ] Persist web debate runs to disk, for example `results/web_debate_runs.json`.
- [ ] Load saved web debates into the Record section on page load.
- [ ] Add a clear frontend indication that selector mode supports two to four solvers.
- [ ] Avoid spending more time on visual polish until dataset and evaluation are complete.

### GitHub / Submission

- [ ] Push final work to GitHub.
- [ ] Make sure all required contributors have commits.
- [ ] Include notebook.
- [ ] Include generated plots.
- [ ] Include README/run instructions.
- [ ] Include enough saved result artifacts for grading, if allowed by submission rules.

## Work Split

### Person 1: Pipeline / Backend

Main responsibility: make the assignment workflow reliable.

- [x] Implement all pipeline stages.
- [x] Update `main.py`.
- [x] Save complete debate runs.
- [ ] Run and validate the pipeline on the full dataset.
- [ ] Fix any malformed JSON or API failure cases discovered during real runs.

Estimated project weight: 40%.

### Person 2: Dataset / Evaluation

Main responsibility: make the project measurable.

- [ ] Build the full 25-problem dataset.
- [ ] Add expected answers and grading notes.
- [ ] Implement baselines.
- [ ] Implement metrics.
- [ ] Implement plots.
- [ ] Create/update notebook analysis.
- [ ] Compare full debate system to baselines.

Estimated project weight: 35%.

### Person 3: Agents / Frontend / Documentation

Main responsibility: keep the concept coherent and make the project demo-ready.

- [x] Build the Agon interface.
- [x] Keep API keys out of frontend code.
- [x] Add README setup basics.
- [x] Align frontend demo behavior with the final pipeline.
- [x] Add frontend controls for auto/manual role assignment.
- [ ] Expand README for final submission.
- [ ] Prepare presentation explanation.
- [ ] Explain why the philosopher framing satisfies the original assignment.

Estimated project weight: 25%.

## Recommended Priority

1. Build the 25-problem dataset.
2. Run and validate the full pipeline on a small limit, then on the full dataset.
3. Implement baselines, metrics, and plots.
4. Create the analysis notebook.
5. Expand README and submission documentation.
6. Polish the frontend only after required backend/evaluation artifacts are complete.

## Suggested Command Flow

```bash
pip install -r requirements.txt
python main.py --limit 1
python main.py
python web_app.py
```

Then open:

```text
http://127.0.0.1:8000
```

Suggested `.env`:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5-mini
```
