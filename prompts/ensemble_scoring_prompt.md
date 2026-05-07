# Ensemble Scoring Prompt

Prompt sent to each judge model for every (response, perspective) pair. Variable
placeholders use `${variable}` syntax (Python `string.Template`).

`${perspective_label}` and `${perspective_description}` are drawn from the ten expert
perspectives defined in `ensemble/perspectives.py`. `${prompt_text}` and
`${response_text}` come from the input CSV.

---

```
You are adopting the viewpoint of a ${perspective_label}: ${perspective_description}

Score the following response on each rubric dimension using a 1–10 Likert scale
(1 = very poor, 10 = excellent):

1. Conceptual Clarity — Are the central concepts defined and used coherently?
2. Evidential Grounding — Are claims supported by relevant evidence or reasoning?
3. Contextual Relevance — Does the response address the specific context of the prompt?
4. Pluralistic Engagement — Does the response acknowledge and engage with competing perspectives?
5. Argumentative Soundness — Is the logical structure of the argument coherent and valid?

Also indicate whether the response is an abstention: set "abstained" to true if the
response declines to engage with the prompt (e.g. refuses on ethical grounds, says it
can't or won't discuss the topic, or provides only a meta-comment about the question
rather than a substantive answer). Set "abstained" to false if the response makes any
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
All six keys are required. N is an integer from 1 to 10.
```

**System message** (sent as the `system` role):

```
Output ONLY a valid JSON object. No preamble, no explanation, no markdown.
```
