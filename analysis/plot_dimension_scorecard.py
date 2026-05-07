#!/usr/bin/env python3
"""Dimension scorecard: per-rubric-dimension scores and mean rank by respondent.

Two-panel figure:
  Left  — lollipop scorecard: mean human expert score per rubric dimension,
           one row per respondent (Human Expert, Claude, GPT, Gemini)
  Right — mean expert rank dot-plot (1 = best)

Usage:
    python analysis/plot_dimension_scorecard.py

Outputs:
    figures/dimension_scorecard.pdf
    figures/dimension_scorecard.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.gridspec as gridspec

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))

from config import TASK2_CSV, FIGURES_DIR, RUBRIC_DIMENSIONS, RUBRIC_DIM_LABELS, STANDARD_ITEM_TYPE

matplotlib.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size":         8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "savefig.dpi":       300,
})

DIM_LABELS = [RUBRIC_DIM_LABELS[d] for d in RUBRIC_DIMENSIONS]
DIM_COLORS = ["#E07B39", "#3A86FF", "#06A77D", "#D62246", "#7B2D8B"]
N_DIM      = len(RUBRIC_DIMENSIONS)

RESPONDENTS = ["Human Expert", "Claude 4.6 Opus", "GPT-5.4", "Gemini 3.1 Pro"]
RESP_KEYS   = ["human",        "claude",           "gpt",     "gemini"]
RESP_COLORS = ["#2C3E50",      "#C0392B",           "#2E86AB", "#16A085"]
N_RESP      = len(RESPONDENTS)


def load_human_dim_scores() -> pd.DataFrame:
    df  = pd.read_csv(TASK2_CSV)
    std = df[df["item_type"] == STANDARD_ITEM_TYPE].copy()
    std["respondent"] = std.apply(
        lambda r: r["model"].lower() if r["true_source"] == "model" else "human",
        axis=1,
    )
    return std


def compute_human_agg(std: pd.DataFrame) -> dict[str, dict[str, tuple[float, float]]]:
    """respondent_key → dim_id → (mean, se), averaging across judges then responses."""
    long = std.melt(
        id_vars=["true_id", "respondent"],
        value_vars=RUBRIC_DIMENSIONS,
        var_name="dim", value_name="dim_score",
    )
    long["dim_score"] = pd.to_numeric(long["dim_score"], errors="coerce")
    long = long.dropna(subset=["dim_score"])

    per_resp = (
        long.groupby(["true_id", "respondent", "dim"])["dim_score"]
        .mean().reset_index()
    )
    agg_df = (
        per_resp.groupby(["respondent", "dim"])["dim_score"]
        .agg(["mean", "sem"]).reset_index()
    )

    result: dict = {k: {} for k in RESP_KEYS}
    for _, row in agg_df.iterrows():
        rk = row["respondent"]
        if rk in result:
            result[rk][row["dim"]] = (row["mean"], row["sem"])
    return result


def compute_rank_agg(task2: pd.DataFrame) -> dict[str, tuple[float, float]]:
    std = task2[task2["item_type"] == STANDARD_ITEM_TYPE].copy()
    std["respondent"] = std.apply(
        lambda r: r["model"].lower() if r["true_source"] == "model" else "human",
        axis=1,
    )
    out = {}
    for key in RESP_KEYS:
        rows = std.loc[std["respondent"] == key, "rank"]
        out[key] = (float(rows.mean()), float(rows.sem())) if len(rows) else (np.nan, np.nan)
    return out


def make_scorecard(
    poll_scores: dict[str, dict[str, tuple[float, float]]],
    rank_agg: dict[str, tuple[float, float]],
) -> plt.Figure:
    X_MIN = 4.0
    X_MAX = 10.0

    fig = plt.figure(figsize=(9.5, 6.5))
    gs  = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[3.2, 1.0], wspace=0.08)

    gs_left = gridspec.GridSpecFromSubplotSpec(N_RESP, 1, subplot_spec=gs[0], hspace=0.28)
    lollipop_axes = [fig.add_subplot(gs_left[ri]) for ri in range(N_RESP)]

    scores_by_resp = {
        key: [poll_scores[key].get(d, (np.nan, np.nan))[0] for d in RUBRIC_DIMENSIONS]
        for key in RESP_KEYS
    }
    errors_by_resp = {
        key: [poll_scores[key].get(d, (np.nan, np.nan))[1] for d in RUBRIC_DIMENSIONS]
        for key in RESP_KEYS
    }
    human_scores = scores_by_resp["human"]
    y = np.arange(N_DIM)

    for ri, (key, ax) in enumerate(zip(RESP_KEYS, lollipop_axes)):
        scores = scores_by_resp[key]
        errs   = errors_by_resp[key]

        ax.set_facecolor("#EEF3F8" if ri == 0 else "#FAFAFA")

        for xv in [5, 6, 7, 8, 9, 10]:
            ax.axvline(xv, color="#E0E0E0", lw=0.6, zorder=0)

        if ri > 0:
            for di in range(N_DIM):
                if not np.isnan(human_scores[di]):
                    ax.plot(
                        human_scores[di], di,
                        marker="D", ms=5.5, zorder=5,
                        markerfacecolor="white",
                        markeredgecolor=DIM_COLORS[di],
                        markeredgewidth=1.5, ls="none",
                    )

        for di in range(N_DIM):
            if not np.isnan(scores[di]):
                ax.plot(
                    [X_MIN, scores[di]], [di, di],
                    color=DIM_COLORS[di], lw=1.8, alpha=0.45, zorder=1,
                    solid_capstyle="round",
                )

        for di in range(N_DIM):
            if np.isnan(scores[di]):
                continue
            ax.errorbar(
                scores[di], di, xerr=errs[di],
                fmt="none", ecolor="#333333",
                elinewidth=0.9, capsize=3.5, zorder=3,
            )
            ax.plot(
                scores[di], di,
                marker="o", ms=9, zorder=4,
                color=DIM_COLORS[di], alpha=0.92,
                markeredgecolor="white", markeredgewidth=0.8,
            )
            ax.text(
                scores[di] + 0.15, di, f"{scores[di]:.1f}",
                va="center", ha="left", fontsize=7.5,
                color=DIM_COLORS[di], fontweight="bold", zorder=7,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85),
            )

        ax.set_xlim(X_MIN, X_MAX + 0.6)
        ax.set_ylim(-0.7, N_DIM - 0.3)
        ax.set_yticks(y)
        ax.set_yticklabels(DIM_LABELS, fontsize=8.5, color="#222222")
        ax.set_xticks([4, 5, 6, 7, 8, 9, 10])
        if ri == N_RESP - 1:
            ax.set_xticklabels(["4", "5", "6", "7", "8", "9", "10"], fontsize=8)
            ax.set_xlabel("Human expert rubric score (1-10)", fontsize=8,
                          color="#444444", labelpad=4)
        else:
            ax.set_xticklabels([])

        ax.tick_params(length=0)
        ax.spines["bottom"].set_color("#CCCCCC")
        ax.spines["left"].set_color(RESP_COLORS[ri])
        ax.spines["left"].set_linewidth(3.2)

        ax.set_title(
            RESPONDENTS[ri], fontsize=9.5, fontweight="bold",
            color=RESP_COLORS[ri], loc="left", pad=5,
        )

        mean_r, _ = rank_agg[key]
        rank_str = f"rank: {mean_r:.2f}" if not np.isnan(mean_r) else "rank: —"
        ax.text(
            1.0, 1.0, rank_str, transform=ax.transAxes,
            fontsize=8, color=RESP_COLORS[ri], ha="right", va="bottom",
            fontweight="bold",
            bbox=dict(facecolor="white", edgecolor=RESP_COLORS[ri],
                      boxstyle="round,pad=0.3", linewidth=1.0, alpha=0.9),
        )

    # ── Right panel: mean rank dot-plot ───────────────────────────────────────
    ax_rank = fig.add_subplot(gs[1])
    rank_y  = np.arange(N_RESP)[::-1]

    for ri in range(N_RESP):
        ry = rank_y[ri]
        mean_r, se_r = rank_agg[RESP_KEYS[ri]]
        if not np.isnan(mean_r):
            ax_rank.errorbar(
                mean_r, ry, xerr=se_r,
                fmt="o", ms=9,
                color=RESP_COLORS[ri], alpha=0.92,
                ecolor=RESP_COLORS[ri], elinewidth=1.6, capsize=5.5,
                markeredgecolor="white", markeredgewidth=0.8,
                zorder=3,
            )

    valid_pts = [
        (rank_agg[RESP_KEYS[ri]][0], rank_y[ri], ri)
        for ri in range(N_RESP)
        if not np.isnan(rank_agg[RESP_KEYS[ri]][0])
    ]
    if len(valid_pts) > 1:
        xs = [p[0] for p in valid_pts]
        ys = [p[1] for p in valid_pts]
        ax_rank.plot(xs, ys, color="#AAAAAA", lw=0.8, ls="--", zorder=1)

    sorted_by_rank = sorted(valid_pts, key=lambda p: p[0])
    for ordinal, (mean_r, ry, _) in enumerate(sorted_by_rank, start=1):
        ax_rank.text(
            mean_r, ry + 0.28, f"#{ordinal}",
            ha="center", va="bottom", fontsize=7, color="#555555", fontweight="bold",
        )

    for xv in [1, 2, 3, 4]:
        ax_rank.axvline(xv, color="#E0E0E0", lw=0.6, zorder=0)

    ax_rank.set_xlim(4.7, 1.2)
    ax_rank.set_ylim(-0.7, N_RESP - 0.3)
    ax_rank.set_xticks([4, 3, 2, 1])
    ax_rank.set_xticklabels(["4", "3", "2", "1\n(best)"], fontsize=7.5)
    ax_rank.set_yticks(rank_y)
    ax_rank.set_yticklabels([])
    ax_rank.tick_params(length=0)
    ax_rank.set_xlabel("Expert mean rank", fontsize=8, color="#444444", labelpad=4)
    ax_rank.set_title("Rank\nSummary", fontsize=8.5, fontweight="bold",
                      color="#333333", pad=5, linespacing=1.3)
    ax_rank.spines["bottom"].set_color("#CCCCCC")
    ax_rank.spines["left"].set_color("#CCCCCC")
    ax_rank.set_facecolor("#FAFAFA")

    for ri in range(N_RESP):
        ry = rank_y[ri]
        ax_rank.plot(
            [1.2, 1.2], [ry - 0.4, ry + 0.4],
            color=RESP_COLORS[ri], lw=4, solid_capstyle="round",
            zorder=4, clip_on=False,
        )

    dim_handles = [
        mlines.Line2D([0], [0], marker="o", color="w",
                      markerfacecolor=DIM_COLORS[di], ms=8,
                      label=DIM_LABELS[di])
        for di in range(N_DIM)
    ]
    ref_handle = mlines.Line2D(
        [0], [0], marker="D", color="w",
        markerfacecolor="white", markeredgecolor="#555555",
        markeredgewidth=1.5, ms=6,
        label="Human Expert score (reference)",
    )
    fig.legend(
        handles=dim_handles + [ref_handle],
        loc="lower center", ncol=3, fontsize=7.5,
        frameon=True, framealpha=0.95, edgecolor="#CCCCCC",
        bbox_to_anchor=(0.44, -0.07),
        columnspacing=1.0, handlelength=1.2,
    )

    return fig


def main() -> None:
    if not TASK2_CSV.exists():
        print(f"ERROR: {TASK2_CSV} not found.\nRun: python analysis/download_data.py",
              file=sys.stderr)
        sys.exit(1)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading human dimension scores …")
    std      = load_human_dim_scores()
    poll_agg = compute_human_agg(std)

    print("Response counts per respondent:")
    for key in RESP_KEYS:
        n = std[std["respondent"] == key]["true_id"].nunique()
        judge_col = "judge_id" if "judge_id" in std.columns else "annotator_id"
        print(f"  {key}: {n} unique responses, "
              f"{std[std['respondent'] == key][judge_col].nunique()} judges")

    print("\nLoading human ranks …")
    task2    = pd.read_csv(TASK2_CSV)
    rank_agg = compute_rank_agg(task2)

    print("\nMean ranks:")
    for key in RESP_KEYS:
        mean_r, se_r = rank_agg[key]
        print(f"  {key}: {mean_r:.3f} ± {se_r:.3f}")

    print("\nBuilding scorecard …")
    fig = make_scorecard(poll_agg, rank_agg)

    pdf_path = FIGURES_DIR / "dimension_scorecard.pdf"
    png_path = FIGURES_DIR / "dimension_scorecard.png"
    fig.savefig(pdf_path, bbox_inches="tight", dpi=300, facecolor="white")
    fig.savefig(png_path, bbox_inches="tight", dpi=300, facecolor="white")
    plt.close(fig)

    print(f"\nSaved → {pdf_path}")
    print(f"Saved → {png_path}")


if __name__ == "__main__":
    main()
