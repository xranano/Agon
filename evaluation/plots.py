"""Plot generation for evaluation results. Each plot has a matplotlib-primary
path and a dependency-free SVG fallback, so plots are always generated even
if matplotlib isn't installed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

from config import PLOTS_DIR, RESULTS_DIR

TRADITION_ORDER = ["kant", "nietzsche", "aristotle", "plato", "camus"]
TRADITION_LABELS = {t: t.title() for t in TRADITION_ORDER}
DIFFICULTY_ORDER = ["easy", "medium", "hard"]

SYSTEM_LABELS = {
    "single_agent_baseline": "Single agent",
    "majority_vote_baseline": "Majority vote",
    "full_debate": "Full debate",
}
SYSTEMS = ["single_agent_baseline", "majority_vote_baseline", "full_debate"]


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _save_current(name: str) -> Path:
    if plt is None:
        raise RuntimeError("matplotlib is not available")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = PLOTS_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def _ordered(keys: list[str], preferred_order: list[str]) -> list[str]:
    ordered = [k for k in preferred_order if k in keys]
    ordered += [k for k in sorted(keys) if k not in ordered]
    return ordered


def _plot_bar_svg(name: str, title: str, labels: list[str], values: list[float], y_label: str) -> Path:
    """Minimal dependency-free plot fallback."""

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    width = 860
    height = 460
    left = 80
    bottom = 390
    plot_height = 290
    bar_gap = 18
    bar_width = max(32, int((width - left - 60 - bar_gap * len(labels)) / max(1, len(labels))))
    colors = ["#6b7280", "#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#0891b2"]

    def esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="34" text-anchor="middle" font-family="Arial" font-size="22" font-weight="700">{esc(title)}</text>',
        f'<text x="22" y="{bottom - plot_height / 2}" transform="rotate(-90 22 {bottom - plot_height / 2})" text-anchor="middle" font-family="Arial" font-size="13">{esc(y_label)}</text>',
        f'<line x1="{left}" y1="{bottom}" x2="{width - 40}" y2="{bottom}" stroke="#111827" stroke-width="1"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{left}" y2="{bottom - plot_height}" stroke="#111827" stroke-width="1"/>',
    ]
    for tick in range(6):
        value = tick / 5
        y = bottom - value * plot_height
        parts.append(f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - 40}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.1f}</text>')

    for index, (label, value) in enumerate(zip(labels, values)):
        x = left + 24 + index * (bar_width + bar_gap)
        bar_height = max(0, min(1, value)) * plot_height
        y = bottom - bar_height
        color = colors[index % len(colors)]
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{color}"/>')
        parts.append(f'<text x="{x + bar_width / 2}" y="{y - 8:.1f}" text-anchor="middle" font-family="Arial" font-size="12">{value:.0%}</text>')
        parts.append(f'<text x="{x + bar_width / 2}" y="{bottom + 22}" text-anchor="middle" font-family="Arial" font-size="11">{esc(label)}</text>')

    parts.append("</svg>")
    path = PLOTS_DIR / name
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def _heatmap_color(value: float) -> str:
    v = max(0.0, min(1.0, value))
    r = int(255 - v * (255 - 30))
    g = int(255 - v * (255 - 90))
    b = int(255 - v * (255 - 200))
    return f"rgb({r},{g},{b})"


def _plot_heatmap_svg(
    name: str,
    title: str,
    row_labels: list[str],
    col_labels: list[str],
    matrix: list[list[float]],
    value_fmt: str = "{:.0%}",
) -> Path:
    """Dependency-free NxM grid heatmap, same style family as `_plot_bar_svg`."""

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    cell = 74
    left = 130
    top = 66
    width = left + cell * len(col_labels) + 40
    height = top + cell * len(row_labels) + 30

    def esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="700">{esc(title)}</text>',
    ]
    for j, col_label in enumerate(col_labels):
        x = left + j * cell + cell / 2
        parts.append(
            f'<text x="{x}" y="{top - 10}" text-anchor="middle" font-family="Arial" font-size="12">{esc(col_label)}</text>'
        )
    for i, row_label in enumerate(row_labels):
        y = top + i * cell + cell / 2
        parts.append(
            f'<text x="{left - 10}" y="{y + 4}" text-anchor="end" font-family="Arial" font-size="12">{esc(row_label)}</text>'
        )
        for j in range(len(col_labels)):
            value = matrix[i][j]
            x = left + j * cell
            y_top = top + i * cell
            parts.append(
                f'<rect x="{x}" y="{y_top}" width="{cell}" height="{cell}" fill="{_heatmap_color(value)}" stroke="#e5e7eb"/>'
            )
            parts.append(
                f'<text x="{x + cell / 2}" y="{y_top + cell / 2 + 4}" text-anchor="middle" '
                f'font-family="Arial" font-size="11">{value_fmt.format(value)}</text>'
            )
    parts.append("</svg>")
    path = PLOTS_DIR / name
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# 1. Verdict accuracy per category
# --------------------------------------------------------------------------- #
def plot_verdict_accuracy_by_category(summary: dict[str, Any]) -> Path:
    by_category = summary["verdict_accuracy"]["by_category"]
    categories = sorted(by_category)
    labels = [c.replace("_", " ").title() for c in categories]
    values = [by_category[c]["accuracy"] for c in categories]

    if plt is None:
        return _plot_bar_svg("verdict_accuracy_by_category.svg", "Verdict Accuracy by Category", labels, values, "Accuracy")

    plt.figure(figsize=(10, 5))
    bars = plt.bar(labels, values, color="#2563eb")
    plt.ylim(0, 1.05)
    plt.ylabel("Accuracy")
    plt.title("Verdict Accuracy by Category")
    plt.xticks(rotation=20, ha="right")
    for bar, category in zip(bars, categories):
        agreement = by_category[category]["mean_label_agreement"]
        plt.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
            f"{bar.get_height():.0%}\n(agree {agreement:.0%})", ha="center", fontsize=8,
        )
    return _save_current("verdict_accuracy_by_category.png")


# --------------------------------------------------------------------------- #
# 2. Improvement rate (Stage 1 vs 3), with tie band
# --------------------------------------------------------------------------- #
def plot_improvement_rate(summary: dict[str, Any]) -> Path:
    improvement = summary["improvement_rate"]
    labels = ["Improved", "Tie", "Regressed"]
    values = [improvement["rate"], improvement.get("tie_rate", 0.0), improvement.get("regressed_rate", 0.0)]

    if plt is None:
        return _plot_bar_svg("improvement_rate.svg", "Improvement Rate (Stage 1 -> Stage 3)", labels, values, "Rate")

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values, color=["#16a34a", "#9ca3af", "#dc2626"])
    plt.ylim(0, 1.05)
    plt.ylabel("Rate")
    plt.title(
        f"Improvement Rate (Stage 1 -> Stage 3, winner-only)\n"
        f"position-consistency: {improvement['position_consistency_rate']:.0%}, n={improvement['n']}"
    )
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.0%}", ha="center")
    return _save_current("improvement_rate.png")


# --------------------------------------------------------------------------- #
# 3. Persona distinctness by difficulty
# --------------------------------------------------------------------------- #
def plot_persona_distinctness_by_difficulty(summary: dict[str, Any]) -> Path:
    by_difficulty = summary["persona_distinctness"]["by_difficulty"]
    difficulties = _ordered(list(by_difficulty), DIFFICULTY_ORDER)
    labels = [d.title() for d in difficulties]
    values = [by_difficulty[d]["distinct_rate"] for d in difficulties]

    if plt is None:
        return _plot_bar_svg(
            "persona_distinctness_by_difficulty.svg", "Persona Distinctness by Difficulty (higher = less collapse)",
            labels, values, "Distinct rate",
        )

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values, color="#7c3aed")
    plt.ylim(0, 1.05)
    plt.ylabel("Distinct rate (low = persona collapse)")
    plt.title("Persona Distinctness by Difficulty")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.0%}", ha="center")
    return _save_current("persona_distinctness_by_difficulty.png")


# --------------------------------------------------------------------------- #
# 4. System vs. two baselines
# --------------------------------------------------------------------------- #
def plot_baseline_comparison(summary: dict[str, Any]) -> Path:
    systems_data = summary["baselines"]["systems"]
    systems = [s for s in SYSTEMS if s in systems_data]
    labels = [SYSTEM_LABELS.get(s, s) for s in systems]
    values = [systems_data[s]["accuracy"] for s in systems]

    if plt is None:
        return _plot_bar_svg("baseline_comparison.svg", "Verdict Accuracy by System", labels, values, "Accuracy")

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values, color=["#6b7280", "#2563eb", "#dc2626"])
    plt.ylim(0, 1.05)
    plt.ylabel("Accuracy")
    fallback_rate = summary["baselines"].get("fallback_rate", 0.0)
    plt.title(f"Verdict Accuracy by System\n(majority-vote fallback fired {fallback_rate:.0%} of the time)")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.0%}", ha="center")
    return _save_current("baseline_comparison.png")


# --------------------------------------------------------------------------- #
# 5. Fidelity per philosopher per stage (delta)
# --------------------------------------------------------------------------- #
def plot_fidelity_delta(summary: dict[str, Any]) -> Path:
    fidelity = summary["fidelity"]
    traditions = _ordered(list(fidelity), TRADITION_ORDER)
    labels = [TRADITION_LABELS.get(t, t.title()) for t in traditions]
    stage1 = [fidelity[t]["stage1"] for t in traditions]
    stage3 = [fidelity[t]["stage3"] for t in traditions]

    if plt is None:
        deltas = [fidelity[t]["delta"] for t in traditions]
        return _plot_bar_svg("fidelity_delta.svg", "Fidelity Delta (Stage 3 - Stage 1) per Philosopher", labels, deltas, "Delta")

    x = range(len(traditions))
    width = 0.35
    plt.figure(figsize=(8, 5))
    plt.bar([i - width / 2 for i in x], stage1, width=width, label="Stage 1", color="#9ca3af")
    plt.bar([i + width / 2 for i in x], stage3, width=width, label="Stage 3 (refined)", color="#2563eb")
    plt.xticks(list(x), labels)
    plt.ylim(0, 1.05)
    plt.ylabel("Fidelity score")
    plt.title("Fidelity per Philosopher: Stage 1 vs Stage 3")
    plt.legend()
    for i, t in enumerate(traditions):
        delta = fidelity[t]["delta"]
        plt.text(i, max(stage1[i], stage3[i]) + 0.03, f"{delta:+.0%}", ha="center", fontsize=9)
    return _save_current("fidelity_delta.png")


# --------------------------------------------------------------------------- #
# 6. Judge-bias heatmap (5 judges x winning tradition)
# --------------------------------------------------------------------------- #
def plot_judge_bias_heatmap(summary: dict[str, Any]) -> Path:
    dist = summary["judge_bias"]["winner_tradition_distribution_by_judge"]
    traditions = dist["traditions"]
    labels = [TRADITION_LABELS.get(t, t.title()) for t in traditions]
    matrix = [[dist["proportions"][judge_t][winner_t] for winner_t in traditions] for judge_t in traditions]

    if plt is None:
        return _plot_heatmap_svg("judge_bias_heatmap.svg", "Judge-Bias Heatmap (row=judge, col=winning tradition)", labels, labels, matrix)

    plt.figure(figsize=(7, 6))
    plt.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Winning tradition")
    plt.ylabel("Judge")
    plt.title("Judge-Bias Heatmap\n(row = judge, proportion of wins by tradition)")
    for i in range(len(labels)):
        for j in range(len(labels)):
            plt.text(j, i, f"{matrix[i][j]:.0%}", ha="center", va="center", fontsize=9)
    plt.colorbar(label="Proportion of wins")
    return _save_current("judge_bias_heatmap.png")


# --------------------------------------------------------------------------- #
# 7a. HTWR per judge vs. 1/3 chance line
# --------------------------------------------------------------------------- #
def plot_htwr(summary: dict[str, Any]) -> Path:
    htwr = summary["judge_bias"]["htwr"]
    traditions = _ordered(list(htwr), TRADITION_ORDER)
    labels = [TRADITION_LABELS.get(t, t.title()) for t in traditions]
    values = [htwr[t]["htwr"] or 0.0 for t in traditions]

    if plt is None:
        return _plot_bar_svg("htwr_per_judge.svg", "Home-Tradition Win Rate per Judge (vs 1/3 chance)", labels, values, "HTWR")

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values, color="#dc2626")
    plt.axhline(1 / 3, color="#111827", linestyle="--", linewidth=1, label="Chance baseline (1/3)")
    plt.ylim(0, 1.05)
    plt.ylabel("HTWR")
    plt.title("Home-Tradition Win Rate per Judge")
    plt.legend()
    for bar, tradition in zip(bars, traditions):
        stats = htwr[tradition]
        marker = "*" if stats.get("significant_at_05") else ""
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, f"{bar.get_height():.0%}{marker}", ha="center")
    return _save_current("htwr_per_judge.png")


# --------------------------------------------------------------------------- #
# 7b. 5x5 judge-agreement matrix
# --------------------------------------------------------------------------- #
def plot_judge_agreement_matrix(summary: dict[str, Any]) -> Path:
    agreement = summary["judge_bias"]["agreement_matrix"]
    traditions = agreement["traditions"]
    labels = [TRADITION_LABELS.get(t, t.title()) for t in traditions]
    matrix = agreement["matrix"]
    kappa = summary["judge_bias"].get("fleiss_kappa")

    title = f"Judge-Verdict Agreement Matrix (Fleiss' kappa = {kappa:.2f})" if kappa is not None else "Judge-Verdict Agreement Matrix"

    if plt is None:
        return _plot_heatmap_svg("judge_agreement_matrix.svg", title, labels, labels, matrix)

    plt.figure(figsize=(7, 6))
    plt.imshow(matrix, cmap="Purples", vmin=0, vmax=1)
    plt.xticks(range(len(labels)), labels, rotation=30, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            plt.text(j, i, f"{matrix[i][j]:.0%}", ha="center", va="center", fontsize=9)
    plt.colorbar(label="% problems agreeing")
    return _save_current("judge_agreement_matrix.png")


# --------------------------------------------------------------------------- #
# 8. Camus-deviation score per judge
# --------------------------------------------------------------------------- #
def plot_camus_deviation(summary: dict[str, Any]) -> Path:
    deviation = summary["judge_bias"]["camus_deviation"]
    traditions = _ordered(list(deviation), [t for t in TRADITION_ORDER if t != "camus"])
    labels = [TRADITION_LABELS.get(t, t.title()) for t in traditions]
    values = [deviation[t]["mean_distance"] or 0.0 for t in traditions]

    if plt is None:
        return _plot_bar_svg("camus_deviation.svg", "Camus-Deviation Score per Judge", labels, values, "Mean rank distance (0-4)")

    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values, color="#9c2c53")
    plt.ylim(0, 4.3)
    plt.ylabel("Mean Spearman-footrule distance (0-4)")
    plt.title("Camus-Deviation Score per Judge\n(distance from the neutrality-baseline judge's rankings)")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.05, f"{value:.2f}", ha="center")
    return _save_current("camus_deviation.png")


def main() -> None:
    summary_path = RESULTS_DIR / "evaluation_summary.json"
    if not summary_path.exists():
        raise SystemExit("Run `python -m evaluation.metrics` first.")

    summary = _load_json(summary_path)
    paths = [
        plot_verdict_accuracy_by_category(summary),
        plot_improvement_rate(summary),
        plot_persona_distinctness_by_difficulty(summary),
        plot_baseline_comparison(summary),
        plot_fidelity_delta(summary),
        plot_judge_bias_heatmap(summary),
        plot_htwr(summary),
        plot_judge_agreement_matrix(summary),
        plot_camus_deviation(summary),
    ]
    for path in paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
