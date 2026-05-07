#!/usr/bin/env python3
"""Score responses using the SCRuBEval panel of disciplinary experts.

Runs one judge model across all 10 perspectives for every response in the
input CSV.  Run once per judge to build the full ensemble; outputs can then
be aggregated and passed to plot_scorecard.py.

Input CSV columns (required):
    response_id   — unique identifier for each response
    prompt_text   — the question / prompt that was answered
    response_text — the response to evaluate
    respondent_id — label for the source being scored (e.g. "gpt-4o", "human")

Output CSV columns:
    response_id, respondent_id, judge_model, perspective_id,
    conceptual_clarity, evidential_grounding, contextual_relevance,
    pluralistic_engagement, argumentative_soundness, abstained

Usage:
    python ensemble/score_responses.py \\
        --responses  my_responses.csv \\
        --output-dir scores/ \\
        --judge      gpt-4o-mini \\
        --models     ensemble/models.yaml

    # Dry run (first 5 responses only):
    python ensemble/score_responses.py ... --limit 5
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from string import Template

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perspectives import PERSPECTIVES, RUBRIC_DIMENSIONS, LIKERT_MIN, LIKERT_MAX


# ── Scoring prompt ─────────────────────────────────────────────────────────────
# Uses string.Template (${variable}) rather than str.format() so that curly
# braces in prompt_text or response_text (e.g. code snippets, JSON) are safe.

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 10

_SCORING_PROMPT = Template("""\
You are adopting the viewpoint of a ${perspective_label}: ${perspective_description}

Score the following response on each rubric dimension using a 1–10 Likert scale \
(1 = very poor, 10 = excellent):

1. Conceptual Clarity — Are the central concepts defined and used coherently?
2. Evidential Grounding — Are claims supported by relevant evidence or reasoning?
3. Contextual Relevance — Does the response address the specific context of the prompt?
4. Pluralistic Engagement — Does the response acknowledge and engage with competing perspectives?
5. Argumentative Soundness — Is the logical structure of the argument coherent and valid?

Also indicate whether the response is an abstention: set "abstained" to true if the \
response declines to engage with the prompt (e.g. refuses on ethical grounds, says it \
can't or won't discuss the topic, or provides only a meta-comment about the question \
rather than a substantive answer). Set "abstained" to false if the response makes any \
genuine attempt to address the question, even if poorly.

---
PROMPT: ${prompt_text}
---
RESPONSE TO SCORE: ${response_text}
---
Output ONLY the following JSON object. Fill in every field — do NOT omit any key:
{
  "conceptual_clarity": N,
  "evidential_grounding": N,
  "contextual_relevance": N,
  "pluralistic_engagement": N,
  "argumentative_soundness": N,
  "abstained": true/false
}
All six keys are required. N is an integer from 1 to 10.""")

OUTPUT_COLUMNS = [
    "response_id", "respondent_id", "judge_model", "perspective_id",
    "conceptual_clarity", "evidential_grounding", "contextual_relevance",
    "pluralistic_engagement", "argumentative_soundness", "abstained",
]


# ── Model config loading ───────────────────────────────────────────────────────

def load_model_config(models_yaml: str, judge_name: str) -> dict:
    with open(models_yaml, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    models = data.get("models", {})
    if judge_name not in models:
        print(f"ERROR: judge '{judge_name}' not found in {models_yaml}.", file=sys.stderr)
        print(f"  Available: {list(models.keys())}", file=sys.stderr)
        sys.exit(1)
    cfg = models[judge_name]
    # Expand environment variable references in base_url
    cfg["base_url"] = os.path.expandvars(cfg.get("base_url", ""))
    return cfg


def make_client(cfg: dict) -> tuple[OpenAI, str, str]:
    """Return (client, model_id, token_param)."""
    api_key_env = cfg.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        print(f"ERROR: environment variable {api_key_env!r} is not set.", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(base_url=cfg["base_url"], api_key=api_key)
    return client, cfg["model_id"], cfg.get("token_param", "max_tokens")


# ── API call ───────────────────────────────────────────────────────────────────

def call_score(
    client: OpenAI,
    model_id: str,
    token_param: str,
    prompt: str,
) -> dict:
    """Call the judge model and parse per-dimension scores. Retries up to 3×."""
    params: dict = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": "Output ONLY a valid JSON object. No preamble, no explanation, no markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        token_param: 2000,
    }
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(**params)
            raw = response.choices[0].message.content or ""
            start = raw.find("{")
            if start == -1:
                raise ValueError("No JSON object found in response")
            parsed, _ = json.JSONDecoder().raw_decode(raw, start)
            scores: dict = {}
            for dim in RUBRIC_DIMENSIONS:
                val = parsed.get(dim)
                if val is None:
                    raise ValueError(f"Missing dimension '{dim}'")
                val = int(val)
                if not (LIKERT_MIN <= val <= LIKERT_MAX):
                    raise ValueError(f"Score {val} out of [{LIKERT_MIN}, {LIKERT_MAX}]")
                scores[dim] = val
            raw_abs = parsed.get("abstained", False)
            if isinstance(raw_abs, bool):
                scores["abstained"] = raw_abs
            elif isinstance(raw_abs, str):
                scores["abstained"] = raw_abs.strip().lower() == "true"
            else:
                scores["abstained"] = bool(raw_abs)
            return scores
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_SECONDS * attempt
                print(f"    Attempt {attempt} failed ({exc}). Retrying in {wait}s...",
                      file=sys.stderr)
                time.sleep(wait)
    raise RuntimeError(f"All {MAX_RETRIES} scoring attempts failed") from last_exc


# ── Validation ────────────────────────────────────────────────────────────────

def validate(rows: list[dict], judge_model_id: str, n_responses: int) -> bool:
    passed = True
    expected = n_responses * len(PERSPECTIVES)

    def check(msg: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        status = "PASS" if ok else "FAIL"
        suffix = f" ({detail})" if detail and not ok else ""
        print(f"  [{status}] {msg}{suffix}")
        if not ok:
            passed = False

    print("\nValidation")
    print("=" * 60)
    check(f"Total rows = {expected}", len(rows) == expected, f"got {len(rows)}")

    wrong = [r for r in rows if r["judge_model"] != judge_model_id]
    check("All rows have correct judge_model", not wrong, f"{len(wrong)} wrong")

    n_null = sum(1 for r in rows for d in RUBRIC_DIMENSIONS if not r.get(d))
    check("No null dimension scores", n_null == 0, f"{n_null} null values")

    n_oob = sum(
        1 for r in rows for d in RUBRIC_DIMENSIONS
        if r.get(d) and not (LIKERT_MIN <= int(r[d]) <= LIKERT_MAX)
    )
    check(f"All scores in [{LIKERT_MIN}, {LIKERT_MAX}]", n_oob == 0, f"{n_oob} out-of-bound")

    valid_ids = {p["id"] for p in PERSPECTIVES}
    bad = [r for r in rows if r["perspective_id"] not in valid_ids]
    check("All perspective_ids valid", not bad, f"{len(bad)} invalid")

    abstained = [r for r in rows if str(r.get("abstained", "")).lower() == "true"]
    if abstained:
        print(f"  [WARN] {len(abstained)} abstention rows flagged by judge.")
    else:
        print("  [INFO] No abstentions flagged.")

    print("=" * 60)
    print(f"  Result: {'ALL CHECKS PASSED' if passed else 'SOME CHECKS FAILED'}")
    return passed


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Score responses using the SCRuBEval disciplinary expert panel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--responses", required=True,
                   help="Input CSV (response_id, prompt_text, response_text, respondent_id)")
    p.add_argument("--output-dir", required=True,
                   help="Directory to write scores_<judge>.csv")
    p.add_argument("--judge", required=True,
                   help="Model name as defined in --models YAML (e.g. gpt-4o-mini)")
    p.add_argument("--models", default="ensemble/models.yaml",
                   help="Path to models.yaml (default: ensemble/models.yaml)")
    p.add_argument("--limit", type=int, default=None,
                   help="Score only the first N responses (dry-run)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = load_model_config(args.models, args.judge)
    client, model_id, token_param = make_client(cfg)
    print(f"Judge: {model_id}  (token_param={token_param})")

    with Path(args.responses).open(encoding="utf-8") as f:
        responses = list(csv.DictReader(f))

    required = {"response_id", "prompt_text", "response_text", "respondent_id"}
    missing = required - set(responses[0].keys()) if responses else set()
    if missing:
        print(f"ERROR: input CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    if args.limit is not None:
        responses = responses[: args.limit]
        print(f"DRY RUN: scoring {len(responses)} responses.")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"scores_{args.judge}.csv"

    # Checkpointing: skip already-completed (response_id, perspective_id) pairs
    done_keys: set[tuple[str, str]] = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done_keys.add((r["response_id"], r["perspective_id"]))
        print(f"Resuming: {len(done_keys)} rows already done.\n")

    plan = [(resp, persp) for resp in responses for persp in PERSPECTIVES]
    total = len(plan)
    print(f"Scoring plan: {total} calls ({len(responses)} responses × {len(PERSPECTIVES)} perspectives).\n")

    mode = "a" if done_keys else "w"
    new_count = 0

    with out_path.open(mode, newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=OUTPUT_COLUMNS)
        if not done_keys:
            writer.writeheader()

        for i, (resp, persp) in enumerate(plan, 1):
            rid      = resp["response_id"]
            persp_id = persp["id"]
            key      = (rid, persp_id)

            if key in done_keys:
                continue

            scoring_prompt = _SCORING_PROMPT.safe_substitute(
                perspective_label=persp["label"],
                perspective_description=persp["description"],
                prompt_text=resp["prompt_text"],
                response_text=resp["response_text"],
            )

            if i % 50 == 0:
                print(f"[{i:5d}/{total}] {rid} | {persp_id}")

            try:
                scores = call_score(client, model_id, token_param, scoring_prompt)
            except RuntimeError as exc:
                print(f"    SKIPPING {rid}|{persp_id}: {exc}", file=sys.stderr)
                scores = {d: -1 for d in RUBRIC_DIMENSIONS}
                scores["abstained"] = True

            writer.writerow({
                "response_id":   rid,
                "respondent_id": resp["respondent_id"],
                "judge_model":   model_id,
                "perspective_id": persp_id,
                **scores,
            })
            fout.flush()
            done_keys.add(key)
            new_count += 1

    print(f"\n{new_count} new rows written to {out_path}.")

    with out_path.open(encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    ok = validate(all_rows, model_id, n_responses=len(responses))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
