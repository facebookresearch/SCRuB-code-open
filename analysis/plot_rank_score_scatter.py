#!/usr/bin/env python3
"""Rank-score scatter: human Likert score vs. expert mean rank by respondent source.

Plots one point per response (averaged across judges), with error bars (±1 SE).
Standard items only; coloured and shaped by respondent source.

Usage:
    python analysis/plot_rank_score_scatter.py

Outputs:
    figures/rank_score_scatter.pdf
    figures/rank_score_scatter.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))

from config import TASK2_CSV, FIGURES_DIR, STANDARD_ITEM_TYPE

# ── Paul Tol colour palette (colour-blind safe) ───────────────────────────────
SOURCE_COLORS = {
    "human":  "#117733",
    "claude": "#882255",
    "gpt":    "#DDAA00",
    "gemini": "#44AA99",
}
SOURCE_MARKERS = {
    "human":  "o",
    "claude": "s",
    "gpt":    "^",
    "gemini": "D",
}
SOURCE_LABELS = {
    "human":  "Human Expert",
    "claude": "Claude",
    "gpt":    "GPT",
    "gemini": "Gemini",
}
FILLED = {"human": False, "claude": True, "gpt": True, "gemini": True}
DRAW_ORDER = ["human", "claude", "gpt", "gemini"]
Y_OFFSET = {"human": 0.0, "claude": 0.07, "gpt": -0.07, "gemini": 0.0}


def _apply_pub_style() -> None:
    plt.rcParams.update({
        "font.family":        "sans-serif",
        "font.sans-serif":    ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size":          8,
        "axes.labelsize":     9,
        "axes.titlesize":     9,
        "axes.titleweight":   "bold",
        "axes.linewidth":     0.8,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "xtick.major.width":  0.8,
        "ytick.major.width":  0.8,
        "xtick.minor.width":  0.5,
        "ytick.minor.width":  0.5,
        "xtick.major.size":   3.5,
        "ytick.major.size":   3.5,
        "xtick.direction":    "out",
        "ytick.direction":    "out",
        "grid.linewidth":     0.4,
        "grid.alpha":         0.35,
        "legend.fontsize":    8,
        "legend.framealpha":  0.85,
        "legend.edgecolor":   "0.75",
        "legend.borderpad":   0.4,
        "legend.handlelength": 1.5,
        "savefig.dpi":        300,
        "figure.dpi":         150,
    })


def main() -> None:
    if not TASK2_CSV.exists():
        print(f"ERROR: {TASK2_CSV} not found.\nRun: python analysis/download_data.py",
              file=sys.stderr)
        sys.exit(1)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    _apply_pub_style()

    t2  = pd.read_csv(TASK2_CSV)
    std = t2[t2["item_type"] == STANDARD_ITEM_TYPE].copy()

    # Composite score = sum of 5 dimensions (range 5–50); divide by 5 → 1–10 scale.
    std["norm_score"] = std["score"] / 5

    std["source"] = std.apply(
        lambda r: r["model"].lower() if r["true_source"] == "model" else "human",
        axis=1,
    )

    # NOTE: blinded_labels are randomised per judge; always group by true_id.
    agg = (
        std.groupby(["prompt_id", "true_id", "source"])
        .agg(
            mean_score=("norm_score", "mean"),
            se_score=("norm_score",   "sem"),
            mean_rank=("rank",        "mean"),
            se_rank=("rank",          "sem"),
        )
        .reset_index()
    )

    print(f"N responses (data points): {len(agg)}")
    for src, grp in agg.groupby("source"):
        print(f"  {src}: n={len(grp)}, "
              f"mean_score={grp['mean_score'].mean():.2f}, "
              f"mean_rank={grp['mean_rank'].mean():.2f}")

    fig, ax = plt.subplots(figsize=(5.5, 4.2))

    human_ranks = agg.loc[agg["source"] == "human", "mean_rank"]
    model_ranks = agg.loc[agg["source"] != "human", "mean_rank"]

    if len(human_ranks):
        ax.axvspan(human_ranks.min(), 6.5,
                   alpha=0.08, color=SOURCE_COLORS["human"], zorder=0)
        ax.text(
            6.2, 0.92,
            f"Human zone\n(μ rank = {human_ranks.mean():.2f})",
            transform=ax.get_xaxis_transform(), ha="left", va="top",
            fontsize=7.5, color=SOURCE_COLORS["human"], fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7),
        )
    if len(model_ranks):
        ax.axvspan(0.5, model_ranks.max(),
                   alpha=0.22, color="#4878CF", zorder=0)
        mid_m = (0.5 + model_ranks.max()) / 2
        ax.text(
            mid_m, 0.92,
            f"Model zone\n(μ rank = {model_ranks.mean():.2f})",
            transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=7.5, color="#2255AA", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7),
        )

    for src in DRAW_ORDER:
        rows = agg[agg["source"] == src]
        if rows.empty:
            continue
        ax.errorbar(
            rows["mean_rank"],
            rows["mean_score"] + Y_OFFSET[src],
            xerr=rows["se_rank"],
            yerr=rows["se_score"],
            fmt=SOURCE_MARKERS[src],
            ecolor="#999999", elinewidth=0.6, capsize=2.5, capthick=0.6,
            markersize=6, zorder=3,
            label=SOURCE_LABELS[src],
            mfc=SOURCE_COLORS[src] if FILLED[src] else "none",
            mec=SOURCE_COLORS[src],
            mew=1.2,
        )

    all_x = agg["mean_rank"].values
    all_y = agg["mean_score"].values
    if len(all_x) > 2:
        m, b = np.polyfit(all_x, all_y, 1)
        x_line = np.linspace(0.5, 6.5, 100)
        ax.plot(x_line, m * x_line + b, color="black", lw=1.0,
                linestyle="--", alpha=0.4, zorder=2)

    ax.invert_xaxis()
    ax.set_xlim(6.5, 0.5)
    ax.set_xlabel("Human Expert mean rank (1 = best)")
    ax.set_ylabel("Human Expert Likert score (1-10)")
    ax.set_title("Human expert Likert score vs. mean rank by respondent source")
    ax.set_ylim(1.0, 10.5)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax.legend(title="Source", loc="lower right", bbox_to_anchor=(0.99, 0.01))
    ax.grid(True)

    fig.tight_layout()

    pdf_path = FIGURES_DIR / "rank_score_scatter.pdf"
    png_path = FIGURES_DIR / "rank_score_scatter.png"
    fig.savefig(pdf_path, bbox_inches="tight", dpi=300)
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    plt.close(fig)

    print(f"\nSaved → {pdf_path}")
    print(f"Saved → {png_path}")


if __name__ == "__main__":
    main()
