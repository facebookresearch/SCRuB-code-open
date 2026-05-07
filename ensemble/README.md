# SCRuBEval Panel of Disciplinary Experts

Self-contained implementation of the SCRuBEval Panel of Disciplinary Experts —
a PoLL (Panel of LLM Evaluators) ensemble that scores responses on five rubric
dimensions from ten distinct expert perspectives (five disciplinary, five ideological).

## What this produces

For each response, the ensemble produces **10 scores per judge model** (one per
perspective), covering five rubric dimensions:

| Dimension | What it measures |
|-----------|-----------------|
| Conceptual Clarity | Concepts defined and used coherently |
| Evidential Grounding | Claims supported by evidence or reasoning |
| Contextual Relevance | Response addresses the specific prompt |
| Pluralistic Engagement | Competing perspectives acknowledged |
| Argumentative Soundness | Logical structure coherent and valid |

Each score is on a 1–10 Likert scale.  Running three judges gives 30 scores per
response; `plot_scorecard.py` aggregates these into a publication-ready figure.

## Quick start

### Demo (no API key needed)

Run the scorecard immediately using the bundled example data:

```bash
python ensemble/plot_scorecard.py \
    --scores ensemble/example_scores.csv \
    --output figures/
```

This produces `figures/scorecard.pdf` and `figures/scorecard.png` with three
synthetic respondents so you can verify the setup before running any API calls.

### 1. Configure your judge model

Edit `models.yaml` to uncomment and fill in your preferred provider.
Any provider that exposes an OpenAI-compatible chat completions endpoint works —
cloud APIs (OpenAI, Anthropic, Google, Mistral, Together AI, etc.) or
self-hosted models via vLLM, Ollama, or LiteLLM.

```yaml
# ensemble/models.yaml
models:
  gpt-4o-mini:
    model_id:    "gpt-4o-mini"
    base_url:    "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    token_param: "max_completion_tokens"
```

Set the corresponding environment variable:

```bash
export OPENAI_API_KEY="..."
```

### 2. Prepare your responses CSV

Your input file must have these columns:

| Column | Description |
|--------|-------------|
| `response_id` | Unique identifier for each response |
| `prompt_text` | The question or prompt that was answered |
| `response_text` | The response to evaluate |
| `respondent_id` | Label for the source (e.g. `"gpt-4o"`, `"my-model"`) |

### 3. Score responses

Run once per judge model (or once if using a single judge):

```bash
python ensemble/score_responses.py \
    --responses  my_responses.csv \
    --output-dir scores/ \
    --judge      gpt-4o-mini \
    --models     ensemble/models.yaml
```

For the full 3-judge ensemble, run the command three times with different
`--judge` values.  Each run is checkpoint-aware and can be resumed if interrupted.

Output: `scores/scores_gpt-4o-mini.csv`

### 4. Plot the scorecard

```bash
# Single judge
python ensemble/plot_scorecard.py \
    --scores scores/scores_gpt-4o-mini.csv \
    --output figures/

# Multiple judges (ensemble aggregated automatically)
python ensemble/plot_scorecard.py \
    --scores scores/scores_gpt-4o-mini.csv scores/scores_gpt-4o.csv \
    --output figures/
```

Output: `figures/scorecard.pdf` and `figures/scorecard.png`

## Files

| File | Purpose |
|------|---------|
| `perspectives.py` | Perspective definitions, rubric dimensions, scoring constants |
| `models.yaml` | Judge model configurations (uncomment and fill in your provider) |
| `score_responses.py` | Runs the ensemble scorer; one judge at a time |
| `plot_scorecard.py` | Aggregates scores and generates the scorecard figure |
| `example_scores.csv` | Synthetic example data for zero-config demo |

## Using existing score files

If you have score CSVs with different column names (e.g. `response_model` instead
of `respondent_id`, or a composite response key), pass the appropriate flags:

```bash
python ensemble/plot_scorecard.py \
    --scores data/scores_judge_a.csv data/scores_judge_b.csv \
    --respondent-col response_model \
    --response-id-cols prompt_id condition \
    --output figures/
```

## Perspectives

The ensemble adopts ten expert viewpoints when scoring each response:

**Disciplinary (5):** Academic Sociologist, Moral Philosopher, Academic Historian,
Political Scientist, Ethicist

**Ideological (5):** Conservative Social Theorist, Communitarian Ethicist,
Libertarian Ethicist, Conservative Historian, Progressive Social Theorist

Full descriptions of each perspective are in `config.py`.

## Dry run

To test your setup with minimal API calls:

```bash
python ensemble/score_responses.py \
    --responses  my_responses.csv \
    --output-dir scores/ \
    --judge      gpt-4o-mini \
    --limit      2
```

This scores only the first 2 responses (20 API calls total).
