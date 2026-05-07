#!/usr/bin/env python3
"""Compute human inter-rater reliability (IRR) statistics.

Loads data/task2_human_judgments.csv and computes, for standard items:
  - Per-prompt and mean Kendall's W
  - Ordinal Krippendorff's α
  - Mean pairwise Kendall's τ
  - Full-ranking and Top-1 agreement rates

For calibration items: mean rank of cal_model vs cal_human responses.

Results are printed to stdout and saved to data/irr_stats.json.

Usage:
    python analysis/compute_irr.py
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy.stats as st

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))

from config import TASK2_CSV, DATA_DIR, STANDARD_ITEM_TYPE

SEP  = "=" * 68
SEP2 = "-" * 68


# ── Kendall's W ───────────────────────────────────────────────────────────────

def kendalls_w(matrix: list[list[float]]) -> float:
    """Kendall's W from a rater × item rank matrix (each row = one rater)."""
    n_raters = len(matrix)
    n_items  = len(matrix[0])
    col_sums = [sum(matrix[r][c] for r in range(n_raters)) for c in range(n_items)]
    mean_col = sum(col_sums) / n_items
    S = sum((cs - mean_col) ** 2 for cs in col_sums)
    denom = n_raters ** 2 * (n_items ** 3 - n_items)
    return 12 * S / denom if denom else float("nan")


# ── Ordinal Krippendorff's α ──────────────────────────────────────────────────

def krippendorffs_alpha_ordinal(
    data: list[list[float | None]],
    n_values: int,
) -> float:
    """Ordinal Krippendorff's α.

    Args:
        data: rater × unit matrix; None for missing values.
        n_values: number of distinct ordinal values (e.g. 6 for ranks 1-6).
    """
    n_raters = len(data)
    n_units  = len(data[0]) if data else 0

    c: dict[tuple[int, int], float] = defaultdict(float)
    for u in range(n_units):
        col = [data[r][u] for r in range(n_raters) if data[r][u] is not None]
        m_u = len(col)
        if m_u < 2:
            continue
        weight = 1.0 / (m_u - 1)
        for i in range(m_u):
            for j in range(m_u):
                if i != j:
                    c[(int(col[i]), int(col[j]))] += weight

    n_k: dict[int, float] = defaultdict(float)
    for (k, l), v in c.items():
        n_k[k] += v

    total = sum(n_k.values())
    if total == 0:
        return float("nan")

    def ordinal_d2(k: int, l: int) -> float:
        if k == l:
            return 0.0
        lo, hi = min(k, l), max(k, l)
        inner = sum(n_k[g] for g in range(lo + 1, hi))
        return (inner + (n_k[lo] + n_k[hi]) / 2) ** 2

    D_o = sum(c[(k, l)] * ordinal_d2(k, l) for k, l in c)

    D_e = 0.0
    vals = list(set(k for k, _ in c) | set(l for _, l in c))
    for k in vals:
        for l in vals:
            D_e += n_k[k] * n_k[l] * ordinal_d2(k, l)
    D_e /= (total - 1)

    if D_e == 0:
        return 1.0 if D_o == 0 else float("nan")

    return 1.0 - D_o / D_e


# ── Data loading ──────────────────────────────────────────────────────────────

def load_wide(csv_path: Path) -> tuple[list[dict], list[str]]:
    """Load long-format judgments CSV and pivot to wide (one row per response).

    blinded_label is judge-specific so it is NOT part of the pivot key.
    Returns (wide_rows, judge_ids) where each wide_row has keys:
        prompt_id, true_id, item_type, <judge>_rank ...
    and mean_rank is the mean across judges.
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Identify the judge column: judge_id or annotator_id
    judge_col = "judge_id" if "judge_id" in rows[0] else "annotator_id"

    judges = sorted({r[judge_col] for r in rows if r.get(judge_col)})

    # Key by stable response identity; blinded_label is judge-specific and excluded
    key_fields = ["prompt_id", "true_id", "item_type"]
    index: dict[tuple, dict] = {}
    for r in rows:
        key = tuple(r[f] for f in key_fields)
        if key not in index:
            index[key] = {f: r[f] for f in key_fields}
        jid = r[judge_col]
        try:
            index[key][f"{jid}_rank"] = float(r["rank"])
        except (ValueError, KeyError):
            pass

    # Compute mean_rank across judges
    wide_rows = []
    for key, rec in index.items():
        rank_vals = [rec[f"{j}_rank"] for j in judges if f"{j}_rank" in rec]
        rec["mean_rank"] = sum(rank_vals) / len(rank_vals) if rank_vals else float("nan")
        wide_rows.append(rec)

    return wide_rows, judges


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TASK2_CSV.exists():
        print(f"ERROR: {TASK2_CSV} not found.\nRun: python analysis/download_data.py",
              file=sys.stderr)
        sys.exit(1)

    print(f"\n{SEP}")
    print("SCRuBEval — Human inter-rater reliability")
    print(SEP)

    rows, judges = load_wide(TASK2_CSV)

    standard = [r for r in rows if r.get("item_type") == STANDARD_ITEM_TYPE]
    cal      = [r for r in rows if r.get("item_type") != STANDARD_ITEM_TYPE]

    by_prompt: dict[str, list[dict]] = defaultdict(list)
    for r in standard:
        by_prompt[r["prompt_id"]].append(r)

    prompts_sorted = sorted(by_prompt.keys())
    n_prompts = len(prompts_sorted)
    n_responses_per_prompt = len(next(iter(by_prompt.values())))

    # Rank scale = total items in the ranking block (standard + cal per prompt).
    # Judges rank all items together, so ranks run 1..n_total, not 1..n_standard.
    all_rank_vals = [
        float(r[f"{j}_rank"])
        for r in rows
        for j in judges
        if f"{j}_rank" in r
    ]
    n_rank_values = int(max(all_rank_vals)) if all_rank_vals else n_responses_per_prompt

    print(f"\nStandard items : {len(standard)} ({n_prompts} prompts, "
          f"{n_responses_per_prompt} responses each)")
    print(f"Judges         : {len(judges)}")
    print(f"Cal items      : {len(cal)}")

    # ── Per-prompt Kendall's W ─────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("Kendall's W per standard prompt")
    print(SEP2)

    w_vals: list[float] = []
    prompt_w: dict[str, float] = {}
    all_units_per_judge: dict[str, list[float | None]] = {j: [] for j in judges}

    print(f"  {'Prompt':12s} {'n_judges':>9} {'n_items':>8} {'W':>8}")
    for pid in prompts_sorted:
        prompt_rows = sorted(by_prompt[pid], key=lambda r: r["true_id"])

        matrix: list[list[float]] = []
        for j in judges:
            col = f"{j}_rank"
            row_ranks = []
            for r in prompt_rows:
                try:
                    row_ranks.append(float(r[col]))
                except (ValueError, KeyError):
                    row_ranks.append(float("nan"))
            if not any(math.isnan(v) for v in row_ranks):
                matrix.append(row_ranks)

        for j in judges:
            col = f"{j}_rank"
            for r in prompt_rows:
                try:
                    all_units_per_judge[j].append(float(r[col]))
                except (ValueError, KeyError):
                    all_units_per_judge[j].append(None)

        if len(matrix) < 2:
            print(f"  {pid:12s}  insufficient data")
            continue

        w = kendalls_w(matrix)
        w_vals.append(w)
        prompt_w[pid] = w
        print(f"  {pid:12s} {len(matrix):>9} {len(prompt_rows):>8} {w:>8.3f}")

    print(f"\n  Mean W   : {np.mean(w_vals):.3f}")
    print(f"  Median W : {np.median(w_vals):.3f}")
    print(f"  SD W     : {np.std(w_vals, ddof=1):.3f}")
    print(f"  Range    : {min(w_vals):.3f} to {max(w_vals):.3f}")

    # ── Global Krippendorff's α ────────────────────────────────────────────────
    global_matrix = [all_units_per_judge[j] for j in judges]
    alpha = krippendorffs_alpha_ordinal(global_matrix, n_values=n_rank_values)
    print(f"\n  Ordinal Krippendorff's α (global, all standard items): {alpha:.3f}")

    # ── Mean pairwise Kendall's τ ─────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("Pairwise Kendall's τ (standard items, all prompts)")
    print(SEP2)

    def judge_rank_vector(j: str) -> list[float]:
        out = []
        for pid in prompts_sorted:
            for r in sorted(by_prompt[pid], key=lambda x: x["true_id"]):
                try:
                    out.append(float(r[f"{j}_rank"]))
                except (ValueError, KeyError):
                    out.append(float("nan"))
        return out

    judge_vecs = {j: judge_rank_vector(j) for j in judges}
    tau_vals: list[float] = []
    judge_pairs = list(itertools.combinations(judges, 2))

    print(f"  {'Pair':22s} {'τ':>8} {'p':>8}")
    for j1, j2 in judge_pairs:
        v1, v2 = judge_vecs[j1], judge_vecs[j2]
        pairs = [(a, b) for a, b in zip(v1, v2)
                 if not math.isnan(a) and not math.isnan(b)]
        if len(pairs) < 3:
            continue
        a1, a2 = zip(*pairs)
        res = st.kendalltau(a1, a2)
        tau_vals.append(res.statistic)
        label = f"{j1[:10]}-{j2[:10]}"
        print(f"  {label:22s} {res.statistic:>8.3f} {res.pvalue:>8.4f}")

    mean_pairwise_tau = float(np.mean(tau_vals)) if tau_vals else float("nan")
    print(f"\n  Mean pairwise τ : {mean_pairwise_tau:.3f}")

    # ── Exact agreement ────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("Ranking agreement across prompts")
    print(SEP2)

    full_agree_count = 0
    top1_agree_count = 0

    for pid in prompts_sorted:
        prompt_rows = sorted(by_prompt[pid], key=lambda r: r["true_id"])

        judge_rankings: dict[str, list[tuple[float, str]]] = {}
        for j in judges:
            col = f"{j}_rank"
            try:
                ranked = sorted(
                    [(float(r[col]), r["true_id"]) for r in prompt_rows],
                    key=lambda x: x[0],
                )
                judge_rankings[j] = ranked
            except (ValueError, KeyError):
                pass

        if len(judge_rankings) < 2:
            continue

        orderings = [tuple(lbl for _, lbl in v) for v in judge_rankings.values()]
        if len(set(orderings)) == 1:
            full_agree_count += 1

        tops = [ordering[0] for ordering in orderings]
        if len(set(tops)) == 1:
            top1_agree_count += 1

    print(f"  Full-ranking agreement : {full_agree_count}/{n_prompts} "
          f"({full_agree_count/n_prompts*100:.1f}%)")
    print(f"  Top-1 agreement        : {top1_agree_count}/{n_prompts} "
          f"({top1_agree_count/n_prompts*100:.1f}%)")

    # ── Calibration check ─────────────────────────────────────────────────────
    if cal:
        print(f"\n{SEP2}")
        print("Calibration item check")
        print(SEP2)
        # cal_quality_floor = weak model response (expect high rank / ranked last)
        # cal_source_attribution = human text from known source (expect low rank / ranked first)
        cal_model = [r for r in cal if r.get("item_type") in ("cal_model", "cal_quality_floor")]
        cal_human = [r for r in cal if r.get("item_type") in ("cal_human", "cal_source_attribution")]

        def avg_mean_rank(subset):
            vals = [float(r["mean_rank"]) for r in subset
                    if r.get("mean_rank") and not math.isnan(float(r["mean_rank"]))]
            return (sum(vals) / len(vals) if vals else float("nan")), len(vals)

        mr_cm, n_cm = avg_mean_rank(cal_model)
        mr_ch, n_ch = avg_mean_rank(cal_human)
        print(f"  cal_quality_floor mean rank    : {mr_cm:.2f}  (n={n_cm}, expect high)")
        print(f"  cal_source_attribution mean rank: {mr_ch:.2f}  (n={n_ch}, expect low/1)")

    # ── Save stats ─────────────────────────────────────────────────────────────
    out_path = DATA_DIR / "irr_stats.json"
    stats = {
        "n_prompts_standard": n_prompts,
        "n_judges": len(judges),
        "n_responses_per_prompt": n_responses_per_prompt,
        "mean_kendalls_w": float(np.mean(w_vals)),
        "median_kendalls_w": float(np.median(w_vals)),
        "sd_kendalls_w": float(np.std(w_vals, ddof=1)),
        "per_prompt_w": prompt_w,
        "krippendorffs_alpha_ordinal": float(alpha),
        "mean_pairwise_tau": mean_pairwise_tau,
        "full_ranking_agreement_rate": full_agree_count / n_prompts,
        "top1_agreement_rate": top1_agree_count / n_prompts,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"\n  Stats saved → {out_path}")

    print(f"\n{SEP}")
    print("Done.")
    print(SEP)


if __name__ == "__main__":
    main()
