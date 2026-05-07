"""Perspective and rubric definitions for the SCRuBEval disciplinary expert ensemble.

Defines the 10 expert perspectives (5 disciplinary + 5 ideological), the 5 rubric
dimensions, and shared scoring constants.  Import from here rather than
duplicating these definitions in other scripts.
"""

from __future__ import annotations

# ── Rubric dimensions ─────────────────────────────────────────────────────────

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

# ── Scoring scale ─────────────────────────────────────────────────────────────

LIKERT_MIN = 1
LIKERT_MAX = 10

# ── Perspectives ──────────────────────────────────────────────────────────────
# 5 disciplinary + 5 ideological = 10 perspectives.
# Each judge model evaluates each response from all 10 perspectives, so a
# 3-judge ensemble produces 30 scores per response.

PERSPECTIVES: list[dict] = [
    # ── Disciplinary (5) ──────────────────────────────────────────────────────
    {
        "id":    "sociologist",
        "label": "Academic Sociologist",
        "type":  "disciplinary",
        "description": (
            "Evaluates through the lens of structural forces, power dynamics, and social "
            "stratification, drawing on empirical social science to assess whether claims "
            "about social phenomena are grounded in sociological evidence and theory."
        ),
    },
    {
        "id":    "moral_philosopher",
        "label": "Moral Philosopher",
        "type":  "disciplinary",
        "description": (
            "Evaluates through the lens of applied ethics and normative theory, assessing "
            "the logical coherence of moral arguments, clarity of normative claims, and "
            "whether competing moral frameworks are fairly represented, using analytic "
            "philosophy standards."
        ),
    },
    {
        "id":    "historian",
        "label": "Academic Historian",
        "type":  "disciplinary",
        "description": (
            "Evaluates through the lens of historical evidence and long-run social change, "
            "assessing whether claims are situated in appropriate historical context and "
            "whether the use of historical examples is accurate and relevant."
        ),
    },
    {
        "id":    "political_scientist",
        "label": "Political Scientist",
        "type":  "disciplinary",
        "description": (
            "Evaluates through the lens of comparative politics and public policy, assessing "
            "causal reasoning, the accuracy of claims about political institutions and "
            "democratic processes, and whether arguments are grounded in political science "
            "evidence."
        ),
    },
    {
        "id":    "ethicist",
        "label": "Ethicist",
        "type":  "disciplinary",
        "description": (
            "Evaluates through the lens of applied and professional ethics, assessing how "
            "well the response addresses questions of harm, fairness, and responsibility, "
            "and whether ethical tensions are clearly identified and carefully reasoned."
        ),
    },
    # ── Ideological (5) ───────────────────────────────────────────────────────
    {
        "id":    "conservative_social_theorist",
        "label": "Conservative Social Theorist",
        "type":  "ideological",
        "description": (
            "Evaluates through a lens that emphasises tradition, social order, and individual "
            "agency, and is sceptical of purely structural explanations. Looks for "
            "acknowledgment of the unintended consequences of rapid social change and the "
            "importance of organic social institutions."
        ),
    },
    {
        "id":    "communitarian_ethicist",
        "label": "Communitarian Ethicist",
        "type":  "ideological",
        "description": (
            "Evaluates through a lens that foregrounds community membership and shared "
            "traditions, and is critical of individualist or universalist ethical frameworks "
            "that ignore the situated, relational nature of moral life."
        ),
    },
    {
        "id":    "libertarian_ethicist",
        "label": "Libertarian Ethicist",
        "type":  "ideological",
        "description": (
            "Evaluates through a lens that prioritises individual rights and personal "
            "autonomy, and is sceptical of collectivist reasoning or arguments that "
            "subordinate individual liberty to group outcomes."
        ),
    },
    {
        "id":    "conservative_historian",
        "label": "Conservative Historian",
        "type":  "ideological",
        "description": (
            "Evaluates through a lens that emphasises continuity of institutions and elite "
            "agency in history, and is sceptical of structuralist or materialist explanations "
            "that underweight the role of ideas, leadership, and contingency."
        ),
    },
    {
        "id":    "progressive_social_theorist",
        "label": "Progressive Social Theorist",
        "type":  "ideological",
        "description": (
            "Evaluates through a lens that foregrounds structural inequality, systemic power, "
            "and the lived experience of marginalised groups. Looks for engagement with "
            "intersecting axes of oppression (race, class, gender) and scepticism toward "
            "explanations that naturalise or individualise social outcomes."
        ),
    },
]

assert len(PERSPECTIVES) == 10, f"Expected 10 perspectives, got {len(PERSPECTIVES)}"
