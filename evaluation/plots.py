"""Plot generation for evaluation results."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

from config import PLOTS_DIR, RESULTS_DIR


SYSTEM_LABELS = {
    "single_agent_baseline": "Single agent",
    "majority_vote_baseline": "Majority vote",
    "philosopher_vote_baseline": "Philosopher vote",
    "full_debate": "Full debate",
}


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


def plot_system_accuracy(summary: dict[str, Any]) -> Path:
    systems = list(summary["systems"].keys())
    values = [summary["systems"][system]["accuracy"] for system in systems]
    labels = [SYSTEM_LABELS.get(system, system) for system in systems]

    if plt is None:
        return _plot_bar_svg(
            "system_accuracy.svg",
            "Accuracy by System",
            labels,
            values,
            "Accuracy",
        )

    plt.figure(figsize=(7, 4))
    bars = plt.bar(labels, values, color=["#6b7280", "#2563eb", "#dc2626"])
    plt.ylim(0, 1.05)
    plt.ylabel("Accuracy")
    plt.title("Accuracy by System")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.0%}", ha="center")
    return _save_current("system_accuracy.png")


def plot_category_scores(rows: list[dict[str, Any]]) -> Path:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["category"]][row["system"]].append(float(row["score"]))

    categories = sorted(grouped)
    systems = ["single_agent_baseline", "philosopher_vote_baseline", "full_debate"]
    if plt is None:
        labels = [category.replace("_", " ").title() for category in categories]
        values = [
            sum(grouped[category]["full_debate"]) / max(1, len(grouped[category]["full_debate"]))
            for category in categories
        ]
        return _plot_bar_svg(
            "category_scores.svg",
            "Full Debate Mean Score by Category",
            labels,
            values,
            "Mean score",
        )

    width = 0.24
    x_positions = list(range(len(categories)))

    plt.figure(figsize=(10, 5))
    for index, system in enumerate(systems):
        offsets = [x + (index - 1) * width for x in x_positions]
        values = [
            sum(grouped[category][system]) / max(1, len(grouped[category][system]))
            for category in categories
        ]
        plt.bar(offsets, values, width=width, label=SYSTEM_LABELS[system])

    plt.xticks(x_positions, [category.replace("_", " ").title() for category in categories], rotation=20, ha="right")
    plt.ylim(0, 1.05)
    plt.ylabel("Mean rubric score")
    plt.title("Mean Score by Category")
    plt.legend()
    return _save_current("category_scores.png")


def plot_difficulty_accuracy(rows: list[dict[str, Any]]) -> Path:
    difficulties = ["easy", "medium", "hard"]
    systems = ["single_agent_baseline", "philosopher_vote_baseline", "full_debate"]
    grouped: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["difficulty"]][row["system"]].append(bool(row["correct"]))

    if plt is None:
        values = [
            sum(grouped[difficulty]["full_debate"]) / max(1, len(grouped[difficulty]["full_debate"]))
            for difficulty in difficulties
        ]
        return _plot_bar_svg(
            "difficulty_accuracy.svg",
            "Full Debate Accuracy by Difficulty",
            [difficulty.title() for difficulty in difficulties],
            values,
            "Accuracy",
        )

    plt.figure(figsize=(8, 4.5))
    for system in systems:
        values = [
            sum(grouped[difficulty][system]) / max(1, len(grouped[difficulty][system]))
            for difficulty in difficulties
        ]
        plt.plot(difficulties, values, marker="o", linewidth=2, label=SYSTEM_LABELS[system])

    plt.ylim(0, 1.05)
    plt.ylabel("Accuracy")
    plt.xlabel("Difficulty")
    plt.title("Accuracy by Difficulty")
    plt.legend()
    return _save_current("difficulty_accuracy.png")


def plot_key_rates(summary: dict[str, Any]) -> Path:
    names = ["Improvement", "Consensus", "Judge accuracy"]
    values = [
        summary["improvement_rate"],
        summary["consensus_rate"],
        summary["judge_accuracy"],
    ]

    if plt is None:
        return _plot_bar_svg("debate_rates.svg", "Debate Evaluation Rates", names, values, "Rate")

    plt.figure(figsize=(7, 4))
    bars = plt.bar(names, values, color=["#16a34a", "#7c3aed", "#dc2626"])
    plt.ylim(0, 1.05)
    plt.ylabel("Rate")
    plt.title("Debate Evaluation Rates")
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.0%}", ha="center")
    return _save_current("debate_rates.png")


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


def main() -> None:
    summary_path = RESULTS_DIR / "evaluation_summary.json"
    rows_path = RESULTS_DIR / "evaluation_rows.json"
    if not summary_path.exists() or not rows_path.exists():
        raise SystemExit("Run `python -m evaluation.baseline` and `python -m evaluation.metrics` first.")

    summary = _load_json(summary_path)
    rows = _load_json(rows_path)
    paths = [
        plot_system_accuracy(summary),
        plot_category_scores(rows),
        plot_difficulty_accuracy(rows),
        plot_key_rates(summary),
    ]
    for path in paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
