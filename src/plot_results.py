"""
Charts for the rerun of the paper's experiment. Reads saved outputs and gradings; no API calls.

  experiments/figures/quality.png     pairwise rubric scores per task (each grading + mean)
  experiments/figures/cost_time.png   cost, tokens and wall-clock time per task (each run + mean)

Usage: python src/plot_results.py
"""

import json
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "experiments" / "outputs"
GRADES = ROOT / "experiments" / "evaluations" / "pairwise_opus55"
FIG = ROOT / "experiments" / "figures"

TASKS = [("api_endpoint", "API endpoint\n(simple)"), ("ecommerce", "E-commerce catalog\n(complex)")]
APPROACHES = [("single", "single_agent", "Single agent", "#2a78d6"),
              ("multi", "parallel_multi", "Multi-agent", "#eb6834")]
TEXT, TEXT2, GRID = "#0b0b0b", "#52514e", "#e8e7e3"

plt.rcParams.update({
    "font.family": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 10,
    "text.color": TEXT, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT,
    "axes.edgecolor": GRID, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 200,
})


def style(ax, grid_axis):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def title(fig, text, sub):
    fig.text(0.02, 0.97, text, fontsize=13, fontweight="bold", va="top")
    fig.text(0.02, 0.905, sub, fontsize=9.5, color=TEXT2, va="top")


def legend_handles():
    return [Line2D([], [], marker="o", ls="", color=c, markersize=8, label=label) for _, _, label, c in APPROACHES]


def quality():
    rng = random.Random(0)  # fixed jitter so the figure is reproducible
    fig, ax = plt.subplots(figsize=(8, 3.6))
    fig.subplots_adjust(left=0.24, right=0.97, top=0.76, bottom=0.25)
    for i, (task, label) in enumerate(TASKS):
        y = len(TASKS) - 1 - i
        gradings = [g for f in sorted((GRADES / task).glob("run_*.json"))
                    for g in json.loads(f.read_text())["gradings"] if g.get("single")]
        for key, _, _, color in APPROACHES:
            dy = 0.17 if key == "single" else -0.17
            totals = [g[f"{key}_total"] for g in gradings]
            ax.scatter(totals, [y + dy + rng.uniform(-0.06, 0.06) for _ in totals],
                       s=22, color=color, alpha=0.35, linewidths=0, zorder=2)
            mean = sum(totals) / len(totals)
            ax.scatter(mean, y + dy, s=110, color=color, edgecolors="white", linewidths=1.5, zorder=3)
            ax.text(mean, y + dy + (0.13 if dy > 0 else -0.13), f"{mean:.1f}", ha="center",
                    va="bottom" if dy > 0 else "top", fontsize=9, color=TEXT2)
    ax.set_yticks(range(len(TASKS)), [t[1] for t in reversed(TASKS)])
    ax.set_ylim(-0.65, len(TASKS) - 0.35)
    ax.set_xlim(15, 35)
    ax.set_xticks(range(15, 36, 5))
    ax.set_xlabel("Quality score (out of 40)")
    style(ax, "x")
    handles = legend_handles() + [
        Line2D([], [], marker="o", ls="", color=TEXT2, alpha=0.35, markersize=5, label="One grading"),
        Line2D([], [], marker="o", ls="", color=TEXT2, markersize=9, label="Mean")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=4, frameon=False, fontsize=8.5)
    title(fig, "Quality", "3 runs per task, 4 gradings per run")
    fig.savefig(FIG / "quality.png")
    plt.close(fig)


def cost_time():
    metrics = [("cost_usd", "Cost (USD)", "${:.2f}", 1),
               ("total_tokens", "Tokens (thousands)", "{:.0f}k", 1000),
               ("duration_seconds", "Time (seconds)", "{:.0f}s", 1)]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.6))
    fig.subplots_adjust(left=0.06, right=0.99, top=0.72, bottom=0.2, wspace=0.35)
    for ax, (key, label, fmt, scale) in zip(axes, metrics):
        for t, (task, _) in enumerate(TASKS):
            for j, (_, filename, _, color) in enumerate(APPROACHES):
                runs = [json.loads(f.read_text())["execution"][key] / scale
                        for f in sorted((OUTPUTS / task).glob(f"run_*/{filename}.json"))]
                mean = sum(runs) / len(runs)
                x = t + (j - 0.5) * 0.38
                ax.bar(x, mean, width=0.34, color=color, alpha=0.85)
                ax.scatter([x] * len(runs), runs, s=14, color=TEXT, zorder=3, linewidths=0)
                ax.annotate(fmt.format(mean), (x, max(runs + [mean])), xytext=(0, 6), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8.5, color=TEXT2)
        ax.set_xticks(range(len(TASKS)), ["Simple", "Complex"])
        ax.set_title(label, fontsize=10, loc="left", color=TEXT)
        style(ax, "y")
        ax.margins(y=0.15)
    axes[0].legend(handles=legend_handles() + [Line2D([], [], marker="o", ls="", color=TEXT, markersize=4, label="One run")],
                   loc="upper left", frameon=False, fontsize=8.5)
    title(fig, "Cost, tokens and time", "Bars are means of 3 runs")
    fig.savefig(FIG / "cost_time.png")
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    quality()
    cost_time()
    print(f"Wrote figures to {FIG}")
