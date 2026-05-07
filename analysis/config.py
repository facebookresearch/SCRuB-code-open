"""Shared constants for SCRuBEval reproduction scripts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR    = REPO_ROOT / "data"
FIGURES_DIR = REPO_ROOT / "figures"

TASK2_CSV = DATA_DIR / "task2_human_judgments.csv"

STANDARD_ITEM_TYPE = "standard"

RUBRIC_DIMENSIONS = [
    "conceptual_clarity",
    "evidential_grounding",
    "contextual_relevance",
    "pluralistic_engagement",
    "argumentative_soundness",
]

RUBRIC_DIM_LABELS = {
    "conceptual_clarity":      "Conceptual Clarity",
    "evidential_grounding":    "Evidential Grounding",
    "contextual_relevance":    "Contextual Relevance",
    "pluralistic_engagement":  "Pluralistic Engagement",
    "argumentative_soundness": "Argumentative Soundness",
}
