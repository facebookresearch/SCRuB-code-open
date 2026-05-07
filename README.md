# SCRuB: Social Concept Reasoning under Rubric-Based Evaluation

**SCRuB** is a framework for evaluating how well language models reason about social concepts: abstract ideas and categories that shape human social life, relationships, and institutions.

This repository contains the analysis code and scoring ensemble accompanying the paper. The companion datasets are released separately:

- **SCRuBAnnotations**: human expert annotation judgments (rankings and rubric scores)
- **SCRuBEval**: the evaluation benchmark (prompts and model responses)
- **SCRuBSample**: a curated sample for quick exploration

All three datasets are available on the [SCRuB dataset page](https://anonymous-hf.up.railway.app/a/9yop355zrs2p/).
*(Note: this is a review-period anonymised URL and will be updated to a permanent link on publication.)*

---

## Overview

How well do language models engage with socially contested questions, where the quality of reasoning matters as much as the conclusion? SCRuB addresses this by collecting responses from frontier models and human experts, then having a panel of disciplinary experts evaluate each response across five dimensions of critical thinking using a structured rubric.

This repository provides two things. The `analysis/` scripts characterise how expert judges agree with one another and how model responses compare to human expert responses. The `ensemble/` module implements the Panel of Disciplinary Experts used in the paper as a standalone scoring tool, so the same evaluation can be applied to any set of model outputs.

---

## Setup

```bash
pip install -r requirements.txt
```

Python 3.10+ recommended.

---

## Data

Download `task2_human_judgments.csv` from the SCRuBAnnotations dataset page:

**[https://anonymous-hf.up.railway.app/a/9yop355zrs2p/](https://anonymous-hf.up.railway.app/a/9yop355zrs2p/)**

Place the file in the `data/` directory, then verify:

```bash
python analysis/download_data.py
```

---

## Analysis scripts

Each script runs independently once the data file is in place. The table below maps each script to the corresponding paper output.

| Script | Paper output |
|--------|-------------|
| `analysis/compute_irr.py` | IRR statistics (Table 1; saved to `data/irr_stats.json`) |
| `analysis/plot_rank_score_scatter.py` | Figure 2 (`figures/rank_score_scatter.{pdf,png}`) |
| `analysis/plot_dimension_scorecard.py` | Figure 3 (`figures/dimension_scorecard.{pdf,png}`) |

```bash
# Inter-rater reliability statistics, saved to data/irr_stats.json
python analysis/compute_irr.py

# Rank-score scatter figure -> figures/rank_score_scatter.{pdf,png}
python analysis/plot_rank_score_scatter.py

# Dimension scorecard figure -> figures/dimension_scorecard.{pdf,png}
python analysis/plot_dimension_scorecard.py
```

---

## Applying the Panel of Disciplinary Experts to your own data

The `ensemble/` directory contains a self-contained implementation of the PoLL scoring ensemble. It evaluates responses across ten expert perspectives (five disciplinary, five ideological) on the five rubric dimensions used in the paper.

**Prerequisites:** scoring your own responses requires an API key for a model provider with an OpenAI-compatible endpoint (e.g. OpenAI, Anthropic, Google, Mistral). The demo below requires no API key.

**Quick demo (no API key needed):**

```bash
python ensemble/plot_scorecard.py \
    --scores ensemble/example_scores.csv \
    --output figures/
```

**Scoring your own responses:**

1. Edit `ensemble/models.yaml` to configure your judge model. Any provider with an OpenAI-compatible endpoint works.
2. Set the corresponding API key environment variable (e.g. `export OPENAI_API_KEY="..."`).
3. Prepare a CSV with four columns: `response_id`, `prompt_text`, `response_text`, `respondent_id`.
4. Run the scorer and then plot:

```bash
python ensemble/score_responses.py \
    --responses my_responses.csv \
    --output-dir scores/ \
    --judge my-model \
    --models ensemble/models.yaml

python ensemble/plot_scorecard.py \
    --scores scores/scores_my-model.csv \
    --output figures/
```

See `ensemble/README.md` for full documentation.

---

## Directory structure

```
SCRuB-code-open/
├── README.md
├── LICENSE
├── requirements.txt
├── data/               # place task2_human_judgments.csv here
│   └── .gitkeep
├── figures/            # output directory for generated figures
│   └── .gitkeep
├── prompts/
│   ├── README.md                       # overview of all prompt files
│   ├── rubric.md                       # human annotation rubric (Table 3)
│   ├── ensemble_scoring_prompt.md      # PoLL judge scoring prompt
│   ├── adversarial_transform_prompt.md # adversarial framing transform prompt
│   ├── prompt_generation_bbq.md        # SCRuBEval generation — BBQ
│   ├── prompt_generation_hle.md        # SCRuBEval generation — HLE
│   ├── prompt_generation_model_spec.md # SCRuBEval generation — model specifications
│   └── prompt_quality_filter.md        # prompt quality review guide
├── analysis/
│   ├── config.py                    # shared constants (rubric dimensions, paths)
│   ├── download_data.py             # verifies data file is in place
│   ├── compute_irr.py               # expert agreement statistics
│   ├── plot_rank_score_scatter.py   # rank-score scatter figure
│   └── plot_dimension_scorecard.py  # dimension scorecard figure
└── ensemble/
    ├── README.md                    # ensemble usage documentation
    ├── perspectives.py              # perspective definitions and rubric constants
    ├── models.yaml                  # judge model configurations
    ├── score_responses.py           # score responses using the ensemble
    ├── plot_scorecard.py            # generate a scorecard from score output
    └── example_scores.csv           # synthetic example data for zero-config demo
```

---

## Dataset columns

`task2_human_judgments.csv` (from SCRuBAnnotations) should contain:

| Column | Description |
|--------|-------------|
| `prompt_id` | Prompt identifier |
| `true_id` | Response identifier |
| `blinded_label` | Per-judge blinded label (Response A-F) |
| `item_type` | `standard`, `cal_quality_floor`, or `cal_source_attribution` |
| `true_source` | `model` or `human` |
| `model` | Model family (`claude`, `gpt`, `gemini`) for model responses |
| `rank` | Expert rank for this response (1 = best) |
| `score` | Composite rubric score (sum of five dimensions, range 5-50) |
| `judge_id` | Anonymised expert judge identifier |
| `conceptual_clarity` | Per-dimension score (1-10) |
| `evidential_grounding` | Per-dimension score (1-10) |
| `contextual_relevance` | Per-dimension score (1-10) |
| `pluralistic_engagement` | Per-dimension score (1-10) |
| `argumentative_soundness` | Per-dimension score (1-10) |

---

## Intended use and responsible use

This code and the associated datasets are intended for research purposes. The prompts and responses involve socially contested topics (e.g. questions of fairness, identity, and political morality). The data should not be used to train models without appropriate review, and findings should be interpreted with awareness that expert judgment on contested social questions reflects the perspectives of a particular panel of scholars.

---

## Citation

A BibTeX entry will be added here on publication. Please check back after the camera-ready deadline.

---

## License

This repository is released under the [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.
