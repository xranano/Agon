# existentiAIsm

Structured multi-agent philosophical debate system.

This project modifies the default multi-LLM debate assignment by using philosopher-inspired agents while preserving the required workflow:

1. Role self-assessment
2. Deterministic role assignment
3. Independent solver responses
4. Structured peer review
5. Refinement based on critiques
6. Final judge decision
7. Evaluation against baselines with plots

## Project Structure

```text
existentiAIsm/
  data/
    problems.json
    results/
  agents/
    base_agent.py
    nietzsche.py
    kant.py
    mill.py
    camus.py
  pipeline/
    stage0_assess.py
    stage0_5_assign.py
    stage1_solve.py
    stage2_review.py
    stage3_refine.py
    stage4_judge.py
  evaluation/
    metrics.py
    baseline.py
    plots.py
  website/
    index.html
  notebooks/
    analysis.ipynb
  results/
    plots/
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

Create a `.env` file with your API key:

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-5-mini
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the pipeline:

```bash
python main.py
```

