# Social Concept — Open-Ended Generation Template

<instructions>
You are an expert in social sciences and humanities assessment design. You will be given a social concept along with quoted passages and an interpretation that together illustrate a core social, ethical, or political tension.

Your task is to use this concept as a seed and construct a set of **5 distinct open-ended essay prompts** that require expert-level critical reasoning about how the concept operates in society.

**Generation Requirements:**

1. **Identify the Core Tension:** Use the concept name, the quoted passages, and the interpretation to understand the underlying social, ethical, or political tension at play. The interpretation names the analytical stakes; the quotes provide texture and specificity.

2. **Abstract and Generalize:** The prompts you generate should engage with the concept as it manifests across social institutions, policy, culture, and everyday life. Draw on the full breadth of the concept — not just the specific framing of the quotes. The source quotes come from AI system design documents. Your prompts must engage with the concept as it operates across human society broadly — not limited to AI or technology contexts. At most one of the five prompts may focus on technology or AI; the rest must be grounded in other institutional domains.

3. **Generate 5 Functionally Diverse Prompts:** Construct 5 unique critical thinking prompts. Each prompt must be **functionally diverse** from the others — meaning a reader would immediately recognize each prompt as posing a substantially different analytical challenge. To achieve this, each prompt should vary along at least one of the following dimensions:
   - **Analytical framework or disciplinary lens** (e.g., economic analysis vs. social psychology vs. legal theory vs. political philosophy vs. cultural anthropology)
   - **Level of analysis** (e.g., individual cognition and interpersonal interaction vs. organizational and institutional design vs. structural and systemic forces)
   - **Type of reasoning demanded** (e.g., causal explanation vs. normative evaluation vs. synthesis of competing evidence vs. identification of hidden assumptions vs. tracing second-order effects)
   - **Institutional or empirical grounding** (e.g., healthcare vs. education vs. criminal justice vs. labor markets vs. housing vs. media)

   Do not follow a fixed formula across different source concepts. The combination of dimensions should be driven by what is most analytically interesting for the specific concept at hand.

4. **Formulate as Demanding but Accessible Questions:** The analytical challenge should be demanding enough for an expert, but the language should be clear enough that any educated adult can understand what is being asked. They must be genuinely open-ended, allowing for multiple valid analytical perspectives. The question should pose the analytical challenge directly — do not instruct the respondent on how to answer (e.g., avoid "In your answer, consider..." or "Discuss the role of..."). Concretely, each prompt should require the respondent to (a) draw on established theoretical frameworks or empirical literatures, (b) navigate genuine tensions or trade-offs rather than argue a single position, and (c) produce an argument that could not be answered adequately with common-sense reasoning alone. Not every prompt needs to achieve all three, but every prompt must achieve (c).

5. **Length:** Each prompt should be 2–5 sentences — long enough to establish the analytical depth but concise enough to remain focused.

**Common Failure Modes to Avoid:**
- **Definitional prompts in disguise:** "What is [concept]?" reworded as an essay question. Every prompt must require *analysis*, not *description*.
- **Single-right-answer prompts:** If a prompt has one obviously correct position, it is not genuinely open-ended.
- **Embedded assumptions:** Do not presuppose the existence or direction of a bias in the question itself (e.g., "Why does X lead to Y?" assumes X→Y).
- **Laundry-list prompts:** "Discuss the social, economic, and political dimensions of X" invites shallow enumeration, not focused analysis.

**Output Format:**

First, produce a `<scratchpad>` block where you reason through the core concept, name the broader social mechanism, and plan 5 distinct analytical angles — noting which diversity dimension(s) each varies on. Then output exactly 5 prompt blocks.

Do not include any conversational filler before or after the blocks.

<scratchpad>
[Identify the core social tension. Name the broader social mechanism. List 5 distinct analytical angles you will use, noting which diversity dimension(s) each varies on. Confirm at most one angle is technology/AI-focused.]
</scratchpad>

<prompt_1>
  <diversity_dimensions>[Which dimensions this prompt varies on, e.g., "Legal/institutional analysis; systemic level; normative evaluation"]</diversity_dimensions>
  <underlying_issue>[A 5–15 word label naming the specific analytical angle]</underlying_issue>
  <question>[The full text of the open-ended essay question]</question>
</prompt_1>

(Repeat for <prompt_2> through <prompt_5>)

</instructions>

<input>
  <social_concept>
  {concept_name}
  </social_concept>
  <interpretation>
  {interpretation}
  </interpretation>
  <quote_1>
  {quote_1}
  </quote_1>
  <quote_2>
  {quote_2}
  </quote_2>
</input>
