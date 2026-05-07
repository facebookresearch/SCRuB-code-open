"""Tests for the ensemble/ module.

All tests run offline — no API key or network access required.
Tests are organised into three classes mirroring the three ensemble modules:

  TestPerspectives     — perspectives.py constants and structure
  TestScoreResponses   — score_responses.py parsing, validation, and templating
  TestPlotScorecard    — plot_scorecard.py end-to-end with example_scores.csv
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parents[1]
ENSEMBLE_DIR = REPO_ROOT / "ensemble"
sys.path.insert(0, str(ENSEMBLE_DIR))


# ─── perspectives.py ──────────────────────────────────────────────────────────

class TestPerspectives(unittest.TestCase):

    def setUp(self):
        from perspectives import (
            PERSPECTIVES, RUBRIC_DIMENSIONS, RUBRIC_DIM_LABELS,
            LIKERT_MIN, LIKERT_MAX,
        )
        self.perspectives   = PERSPECTIVES
        self.dimensions     = RUBRIC_DIMENSIONS
        self.dim_labels     = RUBRIC_DIM_LABELS
        self.likert_min     = LIKERT_MIN
        self.likert_max     = LIKERT_MAX

    def test_perspective_count(self):
        self.assertEqual(len(self.perspectives), 10)

    def test_disciplinary_and_ideological_split(self):
        types = [p["type"] for p in self.perspectives]
        self.assertEqual(types.count("disciplinary"), 5)
        self.assertEqual(types.count("ideological"), 5)

    def test_required_fields_present(self):
        for p in self.perspectives:
            for field in ("id", "label", "type", "description"):
                self.assertIn(field, p, msg=f"'{field}' missing from perspective {p.get('id')}")

    def test_ids_are_unique(self):
        ids = [p["id"] for p in self.perspectives]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_empty_descriptions(self):
        for p in self.perspectives:
            self.assertTrue(p["description"].strip(),
                            msg=f"Empty description for perspective '{p['id']}'")

    def test_rubric_dimension_count(self):
        self.assertEqual(len(self.dimensions), 5)

    def test_rubric_dim_labels_match_dimensions(self):
        self.assertEqual(set(self.dim_labels.keys()), set(self.dimensions))

    def test_likert_scale(self):
        self.assertEqual(self.likert_min, 1)
        self.assertEqual(self.likert_max, 10)


# ─── score_responses.py ───────────────────────────────────────────────────────

class TestScoreResponses(unittest.TestCase):

    def setUp(self):
        import score_responses as sr
        self.sr = sr

    # ── YAML loading ──────────────────────────────────────────────────────────

    def _write_yaml(self, content: str, tmp: Path) -> Path:
        p = tmp / "models.yaml"
        p.write_text(content)
        return p

    def test_load_model_config_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = self._write_yaml(
                "models:\n  test-judge:\n    model_id: my-model\n"
                "    base_url: https://api.example.com/v1\n"
                "    api_key_env: MY_KEY\n    token_param: max_tokens\n",
                Path(tmp),
            )
            cfg = self.sr.load_model_config(str(yaml_path), "test-judge")
        self.assertEqual(cfg["model_id"], "my-model")
        self.assertEqual(cfg["token_param"], "max_tokens")

    def test_load_model_config_missing_judge_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = self._write_yaml(
                "models:\n  other-judge:\n    model_id: x\n"
                "    base_url: https://api.example.com/v1\n"
                "    api_key_env: KEY\n    token_param: max_tokens\n",
                Path(tmp),
            )
            with self.assertRaises(SystemExit):
                self.sr.load_model_config(str(yaml_path), "nonexistent")

    # ── Scoring prompt template ───────────────────────────────────────────────

    def test_template_substitution_basic(self):
        result = self.sr._SCORING_PROMPT.safe_substitute(
            perspective_label="Test Expert",
            perspective_description="A test perspective.",
            prompt_text="What is social justice?",
            response_text="Social justice is...",
        )
        self.assertIn("Test Expert", result)
        self.assertIn("What is social justice?", result)
        self.assertIn("Social justice is...", result)

    def test_template_safe_with_json_braces(self):
        """Curly braces in response text must not crash safe_substitute."""
        result = self.sr._SCORING_PROMPT.safe_substitute(
            perspective_label="Test Expert",
            perspective_description="A test perspective.",
            prompt_text="Describe a JSON structure.",
            response_text='{"key": "value", "nested": {"a": 1}}',
        )
        self.assertIn('{"key": "value"', result)

    def test_template_safe_with_curly_brace_only_text(self):
        result = self.sr._SCORING_PROMPT.safe_substitute(
            perspective_label="X",
            perspective_description="Y.",
            prompt_text="{unusual { text }",
            response_text="} another { odd } response {",
        )
        self.assertIn("{unusual", result)

    # ── JSON response parsing (call_score internals) ──────────────────────────

    def _parse_scores(self, raw: str) -> dict:
        """Replicate the JSON extraction logic from call_score."""
        from perspectives import RUBRIC_DIMENSIONS, LIKERT_MIN, LIKERT_MAX
        start = raw.find("{")
        if start == -1:
            raise ValueError("No JSON object found")
        parsed, _ = json.JSONDecoder().raw_decode(raw, start)
        scores: dict = {}
        for dim in RUBRIC_DIMENSIONS:
            val = parsed.get(dim)
            if val is None:
                raise ValueError(f"Missing dimension '{dim}'")
            val = int(val)
            if not (LIKERT_MIN <= val <= LIKERT_MAX):
                raise ValueError(f"Out of range: {val}")
            scores[dim] = val
        raw_abs = parsed.get("abstained", False)
        scores["abstained"] = raw_abs if isinstance(raw_abs, bool) else str(raw_abs).lower() == "true"
        return scores

    def test_parse_clean_json(self):
        raw = json.dumps({
            "conceptual_clarity": 8,
            "evidential_grounding": 7,
            "contextual_relevance": 9,
            "pluralistic_engagement": 6,
            "argumentative_soundness": 8,
            "abstained": False,
        })
        scores = self._parse_scores(raw)
        self.assertEqual(scores["conceptual_clarity"], 8)
        self.assertFalse(scores["abstained"])

    def test_parse_json_with_preamble(self):
        raw = 'Here is my rating:\n{"conceptual_clarity":7,"evidential_grounding":6,' \
              '"contextual_relevance":8,"pluralistic_engagement":5,' \
              '"argumentative_soundness":7,"abstained":false}'
        scores = self._parse_scores(raw)
        self.assertEqual(scores["contextual_relevance"], 8)

    def test_parse_rejects_out_of_range(self):
        raw = json.dumps({
            "conceptual_clarity": 11,
            "evidential_grounding": 7,
            "contextual_relevance": 9,
            "pluralistic_engagement": 6,
            "argumentative_soundness": 8,
            "abstained": False,
        })
        with self.assertRaises(ValueError):
            self._parse_scores(raw)

    def test_parse_rejects_missing_dimension(self):
        raw = json.dumps({
            "conceptual_clarity": 8,
            "evidential_grounding": 7,
            "abstained": False,
        })
        with self.assertRaises(ValueError):
            self._parse_scores(raw)

    def test_parse_rejects_no_json(self):
        with self.assertRaises(ValueError):
            self._parse_scores("No JSON here at all.")

    # ── validate() ────────────────────────────────────────────────────────────

    def _make_valid_rows(self, n: int = 1) -> list[dict]:
        from perspectives import PERSPECTIVES, RUBRIC_DIMENSIONS
        rows = []
        for i in range(n):
            for p in PERSPECTIVES:
                rows.append({
                    "response_id":   f"r{i}",
                    "respondent_id": "model-a",
                    "judge_model":   "test-model",
                    "perspective_id": p["id"],
                    **{d: 7 for d in RUBRIC_DIMENSIONS},
                    "abstained": False,
                })
        return rows

    def test_validate_passes_on_valid_rows(self):
        rows = self._make_valid_rows(n=2)
        ok = self.sr.validate(rows, judge_model_id="test-model", n_responses=2)
        self.assertTrue(ok)

    def test_validate_fails_wrong_row_count(self):
        rows = self._make_valid_rows(n=1)
        ok = self.sr.validate(rows, judge_model_id="test-model", n_responses=2)
        self.assertFalse(ok)

    def test_validate_fails_wrong_judge_model(self):
        rows = self._make_valid_rows(n=1)
        ok = self.sr.validate(rows, judge_model_id="other-model", n_responses=1)
        self.assertFalse(ok)

    # ── Input CSV column validation ───────────────────────────────────────────

    def test_required_columns_accepted(self):
        required = {"response_id", "prompt_text", "response_text", "respondent_id"}
        row = {c: "x" for c in required}
        missing = required - set(row.keys())
        self.assertEqual(missing, set())

    def test_missing_column_detected(self):
        required = {"response_id", "prompt_text", "response_text", "respondent_id"}
        row = {"response_id": "x", "prompt_text": "y"}
        missing = required - set(row.keys())
        self.assertEqual(missing, {"response_text", "respondent_id"})


# ─── plot_scorecard.py ────────────────────────────────────────────────────────

class TestPlotScorecard(unittest.TestCase):
    """End-to-end tests using the bundled example_scores.csv — no API needed."""

    EXAMPLE_CSV = ENSEMBLE_DIR / "example_scores.csv"

    def test_example_csv_exists(self):
        self.assertTrue(self.EXAMPLE_CSV.exists(),
                        "ensemble/example_scores.csv is missing")

    def test_example_csv_has_required_columns(self):
        with open(self.EXAMPLE_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = set(reader.fieldnames or [])

        required = {
            "response_id", "respondent_id", "judge_model", "perspective_id",
            "conceptual_clarity", "evidential_grounding", "contextual_relevance",
            "pluralistic_engagement", "argumentative_soundness", "abstained",
        }
        self.assertTrue(required.issubset(header),
                        f"Missing columns: {required - header}")

    def test_example_csv_has_expected_respondents(self):
        with open(self.EXAMPLE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        respondents = {r["respondent_id"] for r in rows}
        self.assertGreaterEqual(len(respondents), 2,
                                "example_scores.csv should have at least 2 respondents")

    def test_example_csv_scores_in_range(self):
        dims = [
            "conceptual_clarity", "evidential_grounding", "contextual_relevance",
            "pluralistic_engagement", "argumentative_soundness",
        ]
        with open(self.EXAMPLE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            for d in dims:
                val = int(row[d])
                self.assertGreaterEqual(val, 1, f"{d}={val} below 1 in row {row}")
                self.assertLessEqual(val, 10, f"{d}={val} above 10 in row {row}")

    def test_plot_scorecard_produces_output_files(self):
        import plot_scorecard
        import matplotlib
        matplotlib.use("Agg")

        with tempfile.TemporaryDirectory() as tmp:
            orig_argv = sys.argv
            sys.argv = [
                "plot_scorecard.py",
                "--scores", str(self.EXAMPLE_CSV),
                "--output", tmp,
            ]
            try:
                plot_scorecard.main()
            finally:
                sys.argv = orig_argv

            self.assertTrue((Path(tmp) / "scorecard.pdf").exists())
            self.assertTrue((Path(tmp) / "scorecard.png").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
