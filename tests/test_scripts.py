"""Tests for SCRuBEval reproduction scripts using the real release dataset."""

from __future__ import annotations

import functools
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "analysis"))

REAL_DATA = REPO_ROOT / "data" / "task2_human_judgments.csv"


def _require_data(test):
    """Skip test if the real data file is not available."""
    @functools.wraps(test)
    def wrapper(self, *args, **kwargs):
        if not REAL_DATA.exists():
            self.skipTest("data/task2_human_judgments.csv not found — run download_data.py")
        return test(self, *args, **kwargs)
    return wrapper


# ─── Unit tests for IRR math ──────────────────────────────────────────────────

class TestKendallsW(unittest.TestCase):

    def test_perfect_agreement(self):
        from compute_irr import kendalls_w
        matrix = [[1, 2, 3, 4, 5, 6]] * 5
        self.assertAlmostEqual(kendalls_w(matrix), 1.0, places=6)

    def test_output_in_range(self):
        from compute_irr import kendalls_w
        import random
        rng = random.Random(7)
        matrix = [list(rng.sample(range(1, 7), 6)) for _ in range(5)]
        w = kendalls_w(matrix)
        self.assertGreaterEqual(w, 0.0)
        self.assertLessEqual(w, 1.0)

    def test_single_item_is_nan(self):
        from compute_irr import kendalls_w
        self.assertTrue(math.isnan(kendalls_w([[1]] * 3)))


class TestKrippendorffsAlpha(unittest.TestCase):

    def test_perfect_agreement(self):
        from compute_irr import krippendorffs_alpha_ordinal
        data = [[1, 2, 3, 4, 5, 6] * 4] * 5
        alpha = krippendorffs_alpha_ordinal(data, n_values=6)
        self.assertAlmostEqual(alpha, 1.0, places=4)

    def test_output_in_range(self):
        from compute_irr import krippendorffs_alpha_ordinal
        import random
        rng = random.Random(13)
        data = [[rng.randint(1, 6) for _ in range(24)] for _ in range(5)]
        alpha = krippendorffs_alpha_ordinal(data, n_values=6)
        self.assertGreaterEqual(alpha, -1.0)
        self.assertLessEqual(alpha, 1.0)

    def test_with_missing(self):
        from compute_irr import krippendorffs_alpha_ordinal
        data = [[1, None, 3, 4], [None, 2, 3, 4], [1, 2, None, 4]]
        alpha = krippendorffs_alpha_ordinal(data, n_values=4)
        self.assertFalse(math.isnan(alpha))

    def test_empty_is_nan(self):
        from compute_irr import krippendorffs_alpha_ordinal
        self.assertTrue(math.isnan(krippendorffs_alpha_ordinal([], n_values=6)))


class TestLoadWide(unittest.TestCase):

    @_require_data
    def test_returns_rows_and_judges(self):
        from compute_irr import load_wide
        rows, judges = load_wide(REAL_DATA)
        self.assertGreater(len(rows), 0)
        self.assertGreater(len(judges), 0)

    @_require_data
    def test_standard_item_count(self):
        from compute_irr import load_wide
        rows, _ = load_wide(REAL_DATA)
        standard = [r for r in rows if r["item_type"] == "standard"]
        # 26 prompts × 6 standard responses = 156
        self.assertEqual(len(standard), 156)

    @_require_data
    def test_judge_rank_columns_present(self):
        from compute_irr import load_wide
        rows, judges = load_wide(REAL_DATA)
        sample = rows[0]
        for j in judges:
            # At least some rows should have this judge's rank
            if f"{j}_rank" in sample:
                self.assertIsInstance(sample[f"{j}_rank"], float)

    @_require_data
    def test_mean_rank_computed(self):
        from compute_irr import load_wide
        rows, _ = load_wide(REAL_DATA)
        for r in rows:
            self.assertIn("mean_rank", r)
            self.assertFalse(math.isnan(float(r["mean_rank"])))


# ─── Integration tests against real data ─────────────────────────────────────

class TestComputeIrrIntegration(unittest.TestCase):

    @_require_data
    def test_irr_produces_json(self):
        import compute_irr

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            orig = compute_irr.DATA_DIR
            compute_irr.DATA_DIR = out_dir
            try:
                compute_irr.main()
            finally:
                compute_irr.DATA_DIR = orig

            stats_path = out_dir / "irr_stats.json"
            self.assertTrue(stats_path.exists())
            with open(stats_path) as f:
                stats = json.load(f)

        for key in ("mean_kendalls_w", "krippendorffs_alpha_ordinal",
                    "mean_pairwise_tau", "n_prompts_standard", "n_judges"):
            self.assertIn(key, stats)

        self.assertEqual(stats["n_prompts_standard"], 26)
        self.assertEqual(stats["n_judges"], 10)
        self.assertAlmostEqual(stats["mean_kendalls_w"], 0.385, delta=0.02)
        self.assertAlmostEqual(stats["krippendorffs_alpha_ordinal"], 0.350, delta=0.02)
        self.assertAlmostEqual(stats["mean_pairwise_tau"], 0.268, delta=0.02)


class TestRankScoreScatter(unittest.TestCase):

    @_require_data
    def test_saves_output_files(self):
        import plot_rank_score_scatter

        with tempfile.TemporaryDirectory() as tmp:
            orig = plot_rank_score_scatter.FIGURES_DIR
            plot_rank_score_scatter.FIGURES_DIR = Path(tmp)
            try:
                plot_rank_score_scatter.main()
            finally:
                plot_rank_score_scatter.FIGURES_DIR = orig

            self.assertTrue((Path(tmp) / "rank_score_scatter.pdf").exists())
            self.assertTrue((Path(tmp) / "rank_score_scatter.png").exists())

    @_require_data
    def test_response_counts(self):
        """Standard items: 26 prompts × 6 responses = 156 data points."""
        import pandas as pd
        import config as cfg

        t2  = pd.read_csv(cfg.TASK2_CSV)
        std = t2[t2["item_type"] == "standard"].copy()
        std["source"] = std.apply(
            lambda r: r["model"].lower() if r["true_source"] == "model" else "human",
            axis=1,
        )
        agg = std.groupby(["prompt_id", "true_id", "source"]).size().reset_index()
        self.assertEqual(len(agg), 156)

    @_require_data
    def test_mean_ranks_match_known_results(self):
        """Key result: Claude ~2.03, GPT ~2.52, Gemini ~2.73, Human ~3.88."""
        import pandas as pd
        import config as cfg

        t2  = pd.read_csv(cfg.TASK2_CSV)
        std = t2[t2["item_type"] == "standard"].copy()
        std["source"] = std.apply(
            lambda r: r["model"].lower() if r["true_source"] == "model" else "human",
            axis=1,
        )
        agg = (std.groupby(["prompt_id", "true_id", "source"])
               .agg(mean_rank=("rank", "mean")).reset_index())

        for src, expected in [("claude", 2.03), ("gpt", 2.52),
                               ("gemini", 2.73), ("human", 3.88)]:
            actual = agg[agg["source"] == src]["mean_rank"].mean()
            self.assertAlmostEqual(actual, expected, delta=0.05,
                                   msg=f"{src} mean rank off")


class TestDimensionScorecard(unittest.TestCase):

    @_require_data
    def test_saves_output_files(self):
        import plot_dimension_scorecard

        with tempfile.TemporaryDirectory() as tmp:
            orig = plot_dimension_scorecard.FIGURES_DIR
            plot_dimension_scorecard.FIGURES_DIR = Path(tmp)
            try:
                plot_dimension_scorecard.main()
            finally:
                plot_dimension_scorecard.FIGURES_DIR = orig

            self.assertTrue((Path(tmp) / "dimension_scorecard.pdf").exists())
            self.assertTrue((Path(tmp) / "dimension_scorecard.png").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
