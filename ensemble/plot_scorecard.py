#!/usr/bin/env python3
"""Generate a SCRuBEval scorecard from ensemble scores.

Produces a lollipop scorecard — one row per respondent, one dot per rubric
dimension — averaged across all perspectives and judge models.  Unlike the
paper figure this script does not include a human expert row; it is designed
for applying the ensemble to model outputs of your choice.

Input: one or more score CSV files produced by score_responses.py (or any CSV
       with per-dimension scores and a respondent column).  All files are
       concatenated before aggregation, so running multiple judges and passing
       all their output CSVs gives the full ensemble view.

Output: scorecard.pdf + scorecard.png in the specified output directory.

Usage:
    # Out-of-the-box demo with bundled example data
    python ensemble/plot_scorecard.py \\
        --scores ensemble/example_scores.csv \\
        --output figures/

    # Your own scores from score_responses.py
    python ensemble/plot_scorecard.py \\
        --scores scores/scores_gpt-4o-mini.csv \\
        --output figures/

    # Multiple judges (ensemble aggregated automatically)
    python ensemble/plot_scorecard.py \\
        --scores scores/scores_judge-a.csv scores/scores_judge-b.csv \\
        --output figures/

    # Existing score files with different column names
    python ensemble/plot_scorecard.py \\
        --scores data/adversarial_scores_claude.csv data/adversarial_scores_gpt.csv \\
        --respondent-col response_model \\
        --response-id-cols prompt_id condition \\
        --output figures/

    # Control which respondents appear and in what order
    python ensemble/plot_scorecard.py \\
        --scores scores/scores_gpt-4o-mini.csv \\
        --respondents gpt-4o claude-3-opus \\
        --output figures/
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perspectives import RUBRIC_DIMENSIONS, RUBRIC_DIM_LABELS, LIKERT_MIN, LIKERT_MAX

# ── Visual constants ──────────────────────────────────────────────────────────

DIM_COLORS = ["#E07B39", "#3A86FF", "#06A77D", "#D62246", "#7B2D8B"]
DIM_LABELS = [RUBRIC_DIM_LABELS[d] for d in RUBRIC_DIMENSIONS]

# Default colour cycle for respondents (up to 8; extended automatically if needed)
DEFAULT_COLORS = [
    "#2E86AB", "#C0392B", "#16A085", "#8E44AD",
    "#D35400", "#27AE60", "#2C3E50", "#E74C3C",
]

matplotlib.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size":         8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "savefig.dpi":       300,
})


# ── Data helpers ──────────────────────────────────────────────────────────────

def load_scores(
    paths: list[str],
    respondent_col: str,
    response_id_cols: list[str],
) -> pd.DataFrame:
    """Load and concatenate score CSVs; normalise to internal column names."""
    frames = []
    for p in paths:
        df = pd.read_csv(p)

        # Normalise respondent column → respondent_id
        if respondent_col != "respondent_id":
            if respondent_col not in df.columns:
                print(f"ERROR: column '{respondent_col}' not found in {p}.", file=sys.stderr)
                print(f"  Available columns: {list(df.columns)}", file=sys.stderr)
                sys.exit(1)
            df = df.rename(columns={respondent_col: "respondent_id"})

        # Normalise response ID columns → response_id (join multiple cols if needed)
        if response_id_cols == ["response_id"]:
            if "response_id" not in df.columns:
                print(f"ERROR: column 'response_id' not found in {p}.\n"
                      f"  Use --response-id-cols to specify which column(s) identify each response.\n"
                      f"  Available: {list(df.columns)}", file=sys.stderr)
                sys.exit(1)
        else:
            missing = [c for c in response_id_cols if c not in df.columns]
            if missing:
                print(f"ERROR: columns {missing} not found in {p}.", file=sys.stderr)
                sys.exit(1)
            df["response_id"] = df[response_id_cols].astype(str).agg("__".join, axis=1)

        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # Drop failure rows (score = -1) and abstentions
    for d in RUBRIC_DIMENSIONS:
        combined[d] = pd.to_numeric(combined[d], errors="coerce")
    combined = combined[
        combined[RUBRIC_DIMENSIONS].apply(
            lambda row: row.between(LIKERT_MIN, LIKERT_MAX).all(), axis=1
        )
    ]
    if "abstained" in combined.columns:
        combined = combined[combined["abstained"].astype(str).str.lower() != "true"]

    return combined


def aggregate(df: pd.DataFrame, respondents: list[str]) -> dict[str, dict[str, tuple[float, float]]]:
    """
    Returns nested dict: respondent_id → dim_id → (mean, se).

    Averaging strategy:
      1. Per (response_id, respondent_id, dim): average across judges × perspectives.
      2. Per (respondent_id, dim): mean ± SE across responses.
    """
    long = df.melt(
        id_vars=["response_id", "respondent_id"],
        value_vars=RUBRIC_DIMENSIONS,
        var_name="dim", value_name="score",
    )
    long["score"] = pd.to_numeric(long["score"], errors="coerce")
    long = long.dropna(subset=["score"])

    per_resp = (
        long.groupby(["response_id", "respondent_id", "dim"])["score"]
        .mean()
        .reset_index()
    )
    agg = (
        per_resp.groupby(["respondent_id", "dim"])["score"]
        .agg(["mean", "sem"])
        .reset_index()
    )

    result: dict = {r: {} for r in respondents}
    for _, row in agg.iterrows():
        rid = row["respondent_id"]
        if rid in result:
            result[rid][row["dim"]] = (row["mean"], float(row["sem"]))
    return result


# ── Figure ────────────────────────────────────────────────────────────────────

def make_scorecard(
    agg_scores: dict[str, dict[str, tuple[float, float]]],
    respondents: list[str],
    resp_colors: list[str],
) -> plt.Figure:
    n_resp = len(respondents)
    n_dim  = len(RUBRIC_DIMENSIONS)
    X_MIN  = 4.0
    X_MAX  = 10.0

    fig = plt.figure(figsize=(8.5, 2.2 * n_resp + 1.0))
    gs  = gridspec.GridSpec(n_resp, 1, figure=fig, hspace=0.35)
    axes = [fig.add_subplot(gs[ri]) for ri in range(n_resp)]

    y = np.arange(n_dim)

    scores_by_resp = {
        r: [agg_scores[r].get(d, (np.nan, np.nan))[0] for d in RUBRIC_DIMENSIONS]
        for r in respondents
    }
    errors_by_resp = {
        r: [agg_scores[r].get(d, (np.nan, np.nan))[1] for d in RUBRIC_DIMENSIONS]
        for r in respondents
    }

    for ri, (resp_id, ax) in enumerate(zip(respondents, axes)):
        scores = scores_by_resp[resp_id]
        errs   = errors_by_resp[resp_id]
        color  = resp_colors[ri]

        ax.set_facecolor("#FAFAFA")
        for xv in [5, 6, 7, 8, 9, 10]:
            ax.axvline(xv, color="#E0E0E0", lw=0.6, zorder=0)

        for di in range(n_dim):
            if not np.isnan(scores[di]):
                ax.plot(
                    [X_MIN, scores[di]], [di, di],
                    color=DIM_COLORS[di], lw=1.8, alpha=0.45, zorder=1,
                    solid_capstyle="round",
                )

        for di in range(n_dim):
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
        ax.set_ylim(-0.7, n_dim - 0.3)
        ax.set_yticks(y)
        ax.set_yticklabels(DIM_LABELS, fontsize=8.5, color="#222222")
        ax.set_xticks([4, 5, 6, 7, 8, 9, 10])
        if ri == n_resp - 1:
            ax.set_xticklabels(["4", "5", "6", "7", "8", "9", "10"], fontsize=8)
            ax.set_xlabel("Ensemble rubric score (1–10)", fontsize=8,
                          color="#444444", labelpad=4)
        else:
            ax.set_xticklabels([])

        ax.tick_params(length=0)
        ax.spines["bottom"].set_color("#CCCCCC")
        ax.spines["left"].set_color(color)
        ax.spines["left"].set_linewidth(3.2)
        ax.set_title(resp_id, fontsize=9.5, fontweight="bold",
                     color=color, loc="left", pad=5)

    # Legend
    handles = [
        mlines.Line2D([0], [0], marker="o", color="w",
                      markerfacecolor=DIM_COLORS[di], ms=8,
                      label=DIM_LABELS[di])
        for di in range(n_dim)
    ]
    fig.legend(
        handles=handles,
        loc="lower center", ncol=3, fontsize=7.5,
        frameon=True, framealpha=0.95, edgecolor="#CCCCCC",
        bbox_to_anchor=(0.44, -0.06),
        columnspacing=1.0, handlelength=1.2,
    )

    return fig


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Plot a SCRuBEval Panel of Disciplinary Experts scorecard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--scores", nargs="+", required=True,
                   help="One or more score CSV files (from score_responses.py or compatible format)")
    p.add_argument("--output", required=True,
                   help="Output directory for scorecard.pdf and scorecard.png")
    p.add_argument("--respondents", nargs="+", default=None,
                   help="Respondent IDs to include and their display order (default: all, sorted)")
    p.add_argument("--respondent-col", default="respondent_id",
                   help="Column name identifying the respondent/model (default: respondent_id). "
                        "Use 'response_model' for adversarial score files.")
    p.add_argument("--response-id-cols", nargs="+", default=["response_id"],
                   help="Column(s) that uniquely identify each response (default: response_id). "
                        "Pass multiple column names to create a composite key, e.g. "
                        "'--response-id-cols prompt_id condition'.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Loading scores from {len(args.scores)} file(s)...")
    df = load_scores(args.scores, args.respondent_col, args.response_id_cols)
    print(f"  {len(df)} valid scoring rows after filtering abstentions.")

    all_respondents = sorted(df["respondent_id"].unique().tolist())
    respondents = args.respondents if args.respondents else all_respondents
    print(f"Respondents: {respondents}")

    missing = [r for r in respondents if r not in df["respondent_id"].values]
    if missing:
        print(f"WARNING: respondents not found in scores: {missing}", file=sys.stderr)
        respondents = [r for r in respondents if r not in missing]

    if not respondents:
        print("ERROR: no valid respondents to plot.", file=sys.stderr)
        sys.exit(1)

    resp_colors = (DEFAULT_COLORS * ((len(respondents) // len(DEFAULT_COLORS)) + 1))[
        : len(respondents)
    ]

    print("Aggregating scores...")
    agg = aggregate(df, respondents)

    print("Building scorecard...")
    fig = make_scorecard(agg, respondents, resp_colors)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "scorecard.pdf"
    png_path = out_dir / "scorecard.png"
    fig.savefig(pdf_path, bbox_inches="tight", dpi=300, facecolor="white")
    fig.savefig(png_path, bbox_inches="tight", dpi=300, facecolor="white")
    plt.close(fig)

    print(f"\nSaved → {pdf_path}")
    print(f"Saved → {png_path}")


if __name__ == "__main__":
    main()
