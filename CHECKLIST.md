# existentiAIsm Checklist

`[x]` done · `[~]` partial · `[ ]` not started

## Cast

- [x] Five philosopher personas (Kant, Nietzsche, Aristotle, Plato, Camus)
- [x] One model, five system prompts

## Phase 1: Dataset

- [x] 25 problems on the new schema (`data/problems.json`)
- [x] Schema fields: `why_this_works`, `annotations`, `expected_strongest_tradition`
- [x] Ground-truth labeling protocol (72.0% inter-annotator agreement)
- [x] `data/validate_problems.py`

## Phase 2: Pipeline

- [x] Stage 0 — role self-assessment
- [x] Stage 0.5 — deterministic role assignment
- [~] Stage 1 — independent solving (free-text, not fully structured)
- [x] Stage 2 — peer review
- [x] Stage 3 — refinement
- [x] Stage 4 — final judgment + rankings
- [x] Stage 4.5 — counterfactual judging
- [~] Persona/stage-instruction separation (no dedicated `agents/personas.py`)

## Phase 3: Evaluation

- [x] Single-agent / majority-vote / full-debate baselines
- [x] Verdict accuracy
- [x] Improvement rate (order-bias controlled)
- [x] Persona distinctness
- [x] Judge reliability
- [x] Fidelity rubric scoring
- [x] Position change per philosopher
- [x] Critique quality proxies
- [x] Judge-bias analysis (HTWR, HTA, agreement matrix + Fleiss' κ, Camus-deviation)
- [x] Inter-annotator agreement reporting
- [x] All 9 plots
- [x] `notebooks/analysis_final.ipynb`
- [ ] Human spot-check sample for critique quality

## Companion Feature: Talk to a Philosopher (Day 2)

- [ ] `chat/chatbot.py`
- [ ] Single-philosopher conversation loop
- [ ] Multi-philosopher room (stretch)

## Deliverables

- [x] Standard repo layout
- [x] `tests/`
- [ ] `agents/personas.py` (persona data not split out yet)
- [ ] `chat/` directory

## Submission

- [ ] Push to GitHub
- [ ] Balance commit history across teammates
- [ ] Commit final `results/` + plots

## Possible Enhancements

- [ ] Grow dataset beyond 25 problems
- [ ] Control for judge-bias confound (persona vs. base-model style)
- [ ] Improve judge reliability on opposed problems (currently chance)
- [ ] Some front-end fixes
