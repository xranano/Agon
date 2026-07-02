# Final Project: Project Existentialism — A Multi-LLM Philosophy Debate System

## Overview

Build a debate system where five LLM instances, each embodying a distinct philosopher, reason about hard ethical and philosophical problems through **structured adversarial review**. Three philosophers independently answer a problem, critique each other's reasoning from their own tradition, refine their positions in light of that critique, and a fourth acts as judge and returns the most defensible answer. Where the standard project combats hallucination through independent solving and peer review, this system stages genuine philosophical conflict — each agent reasons from an incompatible tradition, so a weak argument is exposed not by a checklist but by an opponent who fundamentally disagrees.

**The cast** — five philosophers, any of whom may be assigned Judge on a given problem by the Stage 0.5 algorithm. Per problem: one Judge, three Solvers, one sits out.

| Philosopher | Tradition | In one line |
|---|---|---|
| Immanuel Kant | Deontology | Universal law and duty; persons as ends, never means |
| Friedrich Nietzsche | Master morality | Rejects herd morality and universal duty alike |
| Aristotle | Virtue ethics | The golden mean and human flourishing |
| Plato | Idealism | Eternal Forms and truths beyond appearance |
| Albert Camus | Absurdism | Honesty and clarity over doctrine |

The judge is **not hard-coded**. The system chooses it from the philosophers' self-assessments, which means judge neutrality is itself a variable — and, as it turns out, a finding (see Phase 3, *Judge-Bias Analysis*). To make that analysis causal rather than anecdotal, every problem is **additionally judged counterfactually by all five philosophers** after the debate concludes (see *Counterfactual Judging Protocol*).

Team size: **3**. Contribution must be visible in the Git history (see Submission).

---

## Phase 1: Problem Dataset Construction

Construct a dataset of **25 challenging problems** on which the traditions genuinely disagree.

**Categories** (final distribution):

- Classical ethics & moral dilemmas — 6
- Political philosophy & justice — 5
- Human nature & the good life — 5
- Knowledge, truth & reality — 4
- Power, society & the individual — 5

**Requirements:**

- Each problem must produce a **different answer from each tradition** — if you cannot state what Kant, Nietzsche, Aristotle, and Plato would each conclude, the problem is too weak.
- **Avoid canonical textbook dilemmas** (trolley problem, murderer-at-the-door, Gyges' ring, experience machine). LLMs have memorized the standard positions on these and will recite rather than reason. Prefer concrete, mildly novel scenarios — e.g., "a city considers banning algorithmic rent-pricing," "a scientist must decide whether to publish a result that is true but will be weaponized" — where the tradition must be *applied*, not recalled.
- Problems must be answerable in a focused response, not a dissertation.
- Because these questions have no single objectively correct answer, each problem carries an **`expected_strongest_tradition`** field — the position judged best-defended for that specific problem. This is the proxy ground truth for the accuracy and judge-accuracy metrics in Phase 3, and the philosophy project's substitute for the assignment's "verifiable correct answer" requirement. Its provenance is documented via the labeling protocol below.

### Ground-Truth Labeling Protocol

`expected_strongest_tradition` is not one person's opinion — it is produced by independent annotation:

1. **Independent labeling.** All three team members label every problem independently, before seeing each other's labels: which tradition mounts the strongest defense on *this specific problem*, plus a one-sentence justification. No discussion during labeling.
2. **Agreement measurement.** Compute inter-annotator agreement across the 25 problems — raw percent agreement at minimum, Fleiss' kappa if time allows. Report the number in the final analysis.
3. **Adjudication rule.** A problem's label is accepted when at least **2 of 3 annotators agree**. Problems with a 3-way split are either revised (the split usually means the problem is under-specified) or replaced. Record how many problems required revision — that number is itself part of the dataset-quality story.
4. **Documentation.** Store each annotator's original label in the problem JSON (`annotations` field) so the agreement analysis is reproducible from the repo alone.

State this protocol explicitly in the report. Ground truth with documented, measured provenance is defensible; ground truth by team fiat is not.

### Problem JSON Schema (with validation)

Each problem is stored as structured JSON. `validate_problems.py` must enforce this schema and **fail the build** on violations — it is the dataset-quality gate.

```json
{
  "id": "pol-03",
  "category": "political_philosophy",
  "difficulty": "hard",
  "question": "...",
  "why_this_works": {
    "kant": { "position": "...", "core_reason": "..." },
    "nietzsche": { "position": "...", "core_reason": "..." },
    "aristotle": { "position": "...", "core_reason": "..." },
    "plato": { "position": "...", "core_reason": "..." },
    "camus": { "position": "...", "core_reason": "..." }
  },
  "expected_conflict": "...",
  "difficulty_reason": "...",
  "annotations": {
    "annotator_1": "kant",
    "annotator_2": "kant",
    "annotator_3": "aristotle"
  },
  "expected_strongest_tradition": "kant",
  "label_agreement": "2/3"
}
```

**Validation rules (enforced, not aspirational):**

- All required fields present; `category` and `difficulty` from fixed enums; `id` unique.
- `why_this_works` contains an entry for **all five** philosophers.
- **Distinctness check:** no two traditions may share both the same `position` and the same `core_reason`. Flag any pair whose positions are near-duplicates (simple normalized-string or embedding-similarity check) — if two traditions converge, the problem fails the "genuine disagreement" requirement and must be revised.
- `expected_strongest_tradition` must match the majority of `annotations`, and `label_agreement` must be at least 2/3.
- Category counts must match the distribution above (6/5/5/4/5).
- **Canonical-dilemma blocklist:** reject any `question` containing trolley/murderer-at-the-door/Gyges-style keywords; maintain the blocklist in the validator.

---

## Phase 2: System Implementation

### The Roles

Per problem: three philosopher-Solvers and one philosopher-Judge, chosen by the Stage 0.5 algorithm from the five candidates' self-assessments. One philosopher sits out. The judge is not fixed — Kant, Nietzsche, Aristotle, Plato, or Camus can each end up holding the gavel depending on the problem. This is deliberate: it makes Stage 0 and Stage 0.5 do real work rather than rubber-stamping a predetermined judge, and it turns judge neutrality into something the evaluation can measure.

### Prompt-design principle

Keep each philosopher's **persona** (identity, tone, core commitments, characteristic moves) separate and reusable, and treat the **stage instructions** (the "produce this JSON" part) as a disposable wrapper around it. The same persona object drives every stage — and, later, the companion chatbot. Do not tangle persona and stage logic into one string.

Critically: at every stage, each philosopher reasons **from their own tradition**, not as a neutral grader. A Nietzschean reviewing Kant attacks from Nietzschean ground; that is what makes the debate real rather than a rubric check.

### Workflow — the five stages

All stages produce structured JSON.

**Stage 0 — Role Self-Assessment**
Each of the five philosophers receives the problem and self-assesses whether it is better suited as Solver or Judge, returning confidence scores for both roles.
```json
{
  "philosopher": "nietzsche",
  "role_preferences": ["Solver", "Judge"],
  "confidence_by_role": { "Solver": 0.88, "Judge": 0.55 },
  "reasoning": "This problem demands evaluative force, not neutral arbitration..."
}
```

**Stage 0.5 — Deterministic Role Assignment**
A deterministic algorithm selects one Judge and three Solvers from the five self-assessments (highest Judge confidence wins the role; ties broken by smallest Solver–Judge confidence gap, then alphabetically). The remaining philosopher with the lowest Solver confidence sits out. No philosopher is pre-weighted toward Judge — assignment is driven entirely by self-assessment, which is what makes the judge-bias analysis in Phase 3 meaningful.

**Stage 1 — Independent Solution Generation**
Each of the three Solvers independently produces a reasoned philosophical answer. **No communication between Solvers at this stage.** Each solution states its framework, key considerations, the strongest counterargument it faces, and a clear defensible position — roughly 3–6 sentences of reasoning.
```json
{
  "philosopher": "kant",
  "framework": "The categorical imperative and the formula of humanity",
  "key_considerations": ["Universalizability of the maxim", "Persons as ends"],
  "strongest_counterargument": "Honesty appears in some cases to directly produce harm",
  "position": "...",
  "confidence": 0.83
}
```

**Stage 2 — Peer Review**
Each Solver reviews **every other Solver's** solution (two reviews each), critiquing from its own tradition. Each review checks for: unsupported claims, ignored counterarguments, misattributed views, framework confusion, and incoherence. Each review provides 2 strengths, 2 weaknesses, up to 2 errors, and 2 suggested changes.
```json
{
  "reviewer": "nietzsche",
  "target": "kant",
  "strengths": ["Internally consistent", "Rigorous universalization test"],
  "weaknesses": ["Ignores the life-affirming dimension", "Treats duty as self-evident"],
  "errors": [
    { "location": "Position", "type": "framework_confusion",
      "description": "Mistakes the herd's comfort for a rational necessity",
      "severity": "critical" }
  ],
  "suggested_changes": ["Justify why universal law binds the strong", "Address ressentiment as a source of the maxim"],
  "overall_assessment": "internally_consistent_but_incomplete"
}
```

**Stage 3 — Refinement Based on Feedback**
Each Solver receives its two reviews and revises. It must address each critique explicitly — accept and incorporate valid critiques, or defend its position where a critique is mistaken. Document at most 3 changes.
```json
{
  "philosopher": "kant",
  "changes_made": [
    { "critique": "Ignores real-world consequences", "accepted": false,
      "response": "Consequences are irrelevant to moral worth by definition..." },
    { "critique": "The hard case breaks the rule", "accepted": true,
      "response": "I refine the maxim to distinguish a duty of truthfulness from..." }
  ],
  "refined_position": "...",
  "refined_answer": "...",
  "confidence": 0.90
}
```

**Stage 4 — Final Judgment**
The assigned Judge — whichever philosopher Stage 0.5 selected — receives all three original solutions, all peer reviews, and all three refined solutions, and selects the most defensible refined answer. It prioritizes: soundness of reasoning, engagement with counterarguments, accurate use of the philosopher's actual framework, and honest handling of peer critique (did the solver defend fairly or dodge?).
```json
{
  "judge": "camus",
  "winner": "plato",
  "confidence": 0.84,
  "rankings": ["plato", "kant", "nietzsche"],
  "reasoning": "Plato most consistently engaged the opposing arguments and refined rather than repeated...",
  "final_verdict": "..."
}
```

The winning refined answer is returned to the user as the system's answer.

**Stage 4.5 — Counterfactual Judging (evaluation-only, not part of the user-facing pipeline)**
After Stage 4, the frozen bundle of three refined solutions (plus original solutions and peer reviews) is presented to **each of the other four philosophers as judge**, using the identical Stage 4 judge prompt. This yields **five verdicts per problem — 125 verdicts across the dataset — on identical inputs where judge identity is the only variable.** The assigned judge's verdict remains the system's official answer; the four counterfactual verdicts exist purely to power the Judge-Bias Analysis in Phase 3. Cost: 4 extra API calls per problem (~100 total). Save every counterfactual verdict to `data/results/` alongside the main run.

```json
{
  "problem_id": "pol-03",
  "verdicts": {
    "kant":      { "winner": "kant",      "rankings": ["kant", "aristotle", "nietzsche"], "confidence": 0.86 },
    "nietzsche": { "winner": "nietzsche", "rankings": ["nietzsche", "aristotle", "kant"], "confidence": 0.91 },
    "aristotle": { "winner": "aristotle", "rankings": ["aristotle", "kant", "nietzsche"], "confidence": 0.78 },
    "plato":     { "winner": "kant",      "rankings": ["kant", "aristotle", "nietzsche"], "confidence": 0.74 },
    "camus":     { "winner": "kant",      "rankings": ["kant", "nietzsche", "aristotle"], "confidence": 0.70 }
  },
  "assigned_judge": "camus"
}
```

---

## Phase 3: Evaluation and Analysis

**A note on "correct answers."** These problems have no objectively correct answer. The metrics below are therefore adapted: accuracy is measured against `expected_strongest_tradition` (a proxy ground truth with documented provenance — see the Ground-Truth Labeling Protocol), and the judge is scored on fidelity to each tradition and quality of engagement, not on picking a "true" conclusion. **State this framing explicitly in the report** — it is the honest and defensible way to evaluate a philosophy debate, and graders will expect you to address it head-on. Report the inter-annotator agreement number alongside every accuracy figure: an accuracy metric is only as strong as its labels.

### System-Level Metrics

- **Verdict Accuracy** — % of problems where the assigned judge's winner matches `expected_strongest_tradition`. Always reported with the label-agreement rate as context.
- **Improvement Rate** — % of problems where refined solutions were stronger than the initial solutions, comparing Stage 3 against Stage 1. Judged by an LLM grader **outside any persona** (plain evaluator prompt), with **order-bias control**: every pairwise comparison is run twice with positions swapped (A-vs-B and B-vs-A); a "win" counts only if the same solution wins both orderings, otherwise the pair is recorded as a tie. Report the raw position-consistency rate too — it doubles as a check on grader reliability.
- **Persona Distinctness** (formerly "Consensus Rate") — % of problems where all three Solvers reached the same position independently at Stage 1. In this system a *low* value is the success condition: the agents are prompted from incompatible traditions, so convergence would indicate persona collapse into generic LLM reasoning. Frame it as a sanity check on persona strength, not as agreement quality. If distinct positions drop below ~90% of problems, investigate which personas are collapsing and on which categories.
- **Judge Reliability** — when the three Solvers hold clearly opposed positions, does the assigned Judge pick the one matching expert consensus, and is its stated reasoning internally consistent (rankings compatible with the stated reasons, confidence compatible with the margin)?

### Argument-Quality Metrics

- **Fidelity (rubric-scored, not vibes)** — did each philosopher stay true to their actual tradition, or drift into generic reasoning? Scored by a persona-free LLM grader against a **per-tradition checklist of 3–4 binary criteria**, each scored 0/1, averaged into a fidelity score per solution. Example rubrics:
  - *Kant:* invokes universalizability or the humanity formula • justifies via duty, not outcomes • avoids consequentialist cost-benefit language • treats persons as ends
  - *Nietzsche:* distinguishes master/slave morality or names ressentiment • evaluates by life-affirmation/strength, not universal rules • rejects appeal to universal duty • voice is evaluative, not neutral
  - *Aristotle:* names the relevant virtue(s) and the mean between extremes • argues from eudaimonia/flourishing • attends to character and habituation, not just the act
  - *Plato:* appeals to Forms or an ideal standard beyond appearances • distinguishes opinion from knowledge • argues from the ordered soul or ideal state
  - *Camus:* refuses systematic doctrine • names the absurd or the demand for honesty/lucidity • prioritizes clear-eyed confrontation over consoling answers
  
  Compute fidelity **per stage** (Stage 1 vs Stage 3) and plot the delta: does refinement erode tradition-fidelity? Solvers accepting critiques may drift toward generic compromise — measuring that drift is a real finding either way.
- **Position Change** — how often did a Solver accept a critique and meaningfully revise vs. defend and hold? Computed directly from the `accepted` flags in Stage 3 output; report per philosopher (is Kant more stubborn than Aristotle?).
- **Critique Quality** — did peer reviews identify real weaknesses, or produce boilerplate strengths/weaknesses? Proxy measures: (a) % of critiques that the target explicitly accepted in Stage 3, (b) lexical-diversity check across reviews to flag copy-paste boilerplate, (c) spot-check sample graded by the team.

### Judge-Bias Analysis (the headline finding)

Because Stage 0.5 can appoint any of the five philosophers as Judge, the system has no guaranteed neutral arbiter. A Kantian judge is likely to reward deontological reasoning; a Nietzschean judge will crown whoever is most "life-affirming" and dismiss the rest as herd morality. Rather than hide this, measure it — and thanks to Stage 4.5, measure it **causally**: for every problem, all five philosophers judged the identical solution bundle, so any divergence in verdicts is attributable to judge identity alone.

Definitions: a judge's **home tradition** is its own; the **tradition distance** between winner and judge is 0 if the winner is the judge's own tradition, 1 otherwise (a finer ordinal distance is optional stretch).

- **Home-Tradition Win Rate (HTWR)** — for each judge J, over the problems where J's own tradition appears among the solvers: `HTWR(J) = P(winner's tradition = J's tradition | J judging)`. Chance baseline is 1/3 (three solvers). Report HTWR per judge with a binomial test against 1/3. *This is the single headline number.*
- **Home-Tradition Advantage (HTA)** — the causal version, only possible because of counterfactual judging: for problems where tradition X is a solver, `HTA(X) = P(X wins | X judges) − P(X wins | any other philosopher judges the same bundle)`. Positive HTA = self-preference; report per philosopher.
- **Judge-Verdict Agreement Matrix** — a 5×5 matrix: for each pair of judges, % of problems on which they crowned the same winner. Low off-diagonal agreement is direct evidence that judge identity, not argument quality, drives outcomes. Fleiss' kappa across the five judges gives one summary number.
- **Camus-Deviation Score** — Camus, committed to no ethical system, is the neutrality baseline. For each other judge J: mean rank-distance (Kendall tau or simple rank displacement) between J's rankings and Camus's rankings on the same problems. With counterfactual judging, Camus has a verdict on *all 25 problems*, so no algorithm-nudging is needed to guarantee comparison points.
- **Fairness of Reasoning** — independent of who wins, does the judge's stated reasoning engage each solver's argument, or privilege its own tradition's vocabulary and premises? Proxy: % of the judge's reasoning tokens referencing each solver, plus a vocabulary-overlap score between the judge's reasoning and its own tradition's rubric keywords.

Frame the takeaway honestly: *self-assessed role assignment does not produce a neutral judge, and judge identity is a measurable, causally-isolated source of bias in multi-agent LLM debate.* That is a real, defensible finding — and it distinguishes the project from a wrapper around API calls.

### Baselines

- **Single-LLM Baseline** — ask one philosopher alone; compare its answer to the full-system verdict.
- **Simple Voting Baseline** — take the three independent Stage 1 solutions and pick the majority position (where no majority exists — the common case, given persona distinctness — fall back to highest self-reported confidence, and report how often the fallback fired).
- **Your System** — full debate with peer review, refinement, and judgment.

**Generated plots of all evaluation results are MANDATORY.** At minimum:

1. Verdict accuracy per category
2. Improvement rate (Stage 1 vs Stage 3, with tie band from order-bias control)
3. Persona distinctness by difficulty
4. System vs. two baselines
5. Fidelity per philosopher per stage (Stage 1 vs Stage 3 delta)
6. **Judge-bias heatmap**: 5 judges × winning tradition, built from all 125 counterfactual verdicts
7. HTWR per judge vs. the 1/3 chance line, and the 5×5 judge-agreement matrix
8. Camus-deviation score per judge

---

## Companion Feature: Talk to a Philosopher (Day 2)

A live chat interface where the user picks any one of the five philosophers and converses with them directly. This reuses the debate system's persona objects verbatim — the only new piece is a conversation loop that keeps message history and appends turns. Because the personas were built as reusable objects in Phase 2, the chatbot wraps them in a "you are having a conversation" instruction instead of a "produce Stage N JSON" instruction. The debate pipeline and the chatbot share personas and nothing else, so building the chatbot does not touch the graded debate system.

Optional stretch (only if time allows): a multi-philosopher room where two or three respond to one question and can react to each other. This reintroduces turn-management and the risk of the philosophers converging into agreement, so attempt it only after the single-philosopher chat is solid.

---

## Deliverables

As close as possible to a production-ready system. Code decomposition and structure are up to you. **Generated evaluation plots are a MUST.**

Suggested repository structure:

```
project-existentialism/
├── data/
│   ├── problems.json            # 25 problems, incl. annotations + labels
│   ├── validate_problems.py     # schema + distinctness + blocklist gate
│   └── results/                 # saved debate outputs per run, incl. counterfactual verdicts
├── agents/
│   ├── personas.py              # reusable persona objects (shared by debate + chat)
│   ├── base_agent.py
│   └── kant.py  nietzsche.py  aristotle.py  plato.py  camus.py
├── pipeline/
│   ├── stage0_assess.py  stage0_5_assign.py
│   ├── stage1_solve.py  stage2_review.py  stage3_refine.py  stage4_judge.py
│   └── stage4_5_counterfactual.py
├── evaluation/
│   ├── metrics.py  judge_bias.py  fidelity_rubrics.py  baseline.py  plots.py
├── chat/                        # Day 2 companion feature
│   └── chatbot.py
├── website/index.html           # frontend (debate view + chat panel)
├── notebooks/analysis.ipynb
├── main.py  config.py  requirements.txt  README.md
```

---

## Submission Format

- **GitHub repository link is mandatory.** Repo must contain the notebooks, a README, and instructions to run the code.
- Since this is a **team of three**, commit history must show all three contributed. Do not write offline and upload in one commit.

**Suggested contribution split:**
- **Person 1 — Pipeline:** `stage0_assess.py`, `stage0_5_assign.py`, `stage1_solve.py`, `stage2_review.py`, `stage3_refine.py`, `stage4_judge.py`, `stage4_5_counterfactual.py`
- **Person 2 — Data & evaluation:** `problems.json`, `validate_problems.py`, `metrics.py`, `judge_bias.py`, `fidelity_rubrics.py`, `baseline.py`, `plots.py`, `analysis.ipynb`
- **Person 3 — Personas, chat & frontend:** `personas.py`, the five philosopher prompts, `chatbot.py`, `main.py`, `config.py`, `website/index.html`, `README.md`

(All three annotate the problem dataset independently — see the Ground-Truth Labeling Protocol.)

---

## Model Access

Most models don't have free tiers, so you may need to pay for usage. Two options:

1. Use one free model for all five roles (five API calls to the same model with different system prompts / parameters).
2. Pay the minimum fee (usually ~$5) for paid models.

Either approach is acceptable. Points won't be deducted for using only free models, but they will be deducted for not completing the final task. **API limits are not an accepted excuse for non-delivery** — build in retry and caching, and save every debate run (including all counterfactual verdicts) to `data/results/` so a rate limit never costs you a completed run. Counterfactual judging adds ~100 calls total; budget for it, and cache the frozen Stage 3 bundles so re-judging never re-runs the debate.

---

## Due Date

**3 July, 23:59**
