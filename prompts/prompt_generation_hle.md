# HLE Open-Ended Generation Template

<instructions>
You are an expert in social sciences and humanities assessment design. You will be given an expert-level question from Humanity's Last Exam (HLE), a benchmark of questions designed to be at the frontier of human knowledge. The question may come from any humanities or social science discipline (e.g., philosophy, political science, sociology, history, anthropology, law).

Your task is to use the HLE question as a conceptual seed and construct a set of **5 distinct open-ended essay prompts** that target the broader social, cultural, or institutional concepts underlying the question. These prompts must require expert-level critical reasoning and must be accessible without specialized domain knowledge.

**Generation Requirements:**
1. **Identify the Core Social Concept:** First, identify the underlying social, ethical, or political concept that the HLE question engages with (e.g., distributive justice, epistemic authority, cultural sovereignty, institutional legitimacy, moral relativism). The HLE question may be highly technical or domain-specific — your job is to extract the generalizable social reasoning challenge beneath it.
2. **Abstract and Generalize:** Step back from the specific technical framing of the HLE question. Do not reference the HLE dataset, the specific academic subfield, or any specialized terminology that would require domain expertise to understand. Reframe the concept as an expert-level social reasoning challenge that does not depend on narrow disciplinary knowledge.
3. **Generate 5 Functionally Diverse Prompts:** Construct 5 unique critical thinking prompts. Each prompt must be **functionally diverse** from the others — meaning a reader would immediately recognize each prompt as posing a substantially different analytical challenge. To achieve this, each prompt should vary along at least one of the following dimensions:
   - **Analytical framework or disciplinary lens** (e.g., economic analysis vs. social psychology vs. legal theory vs. political philosophy vs. cultural anthropology)
   - **Level of analysis** (e.g., individual cognition and interpersonal interaction vs. organizational and institutional design vs. structural and systemic forces)
   - **Type of reasoning demanded** (e.g., causal explanation vs. normative evaluation vs. synthesis of competing evidence vs. identification of hidden assumptions vs. tracing second-order effects)
   - **Institutional or empirical grounding** (e.g., healthcare vs. education vs. criminal justice vs. labor markets vs. housing vs. media)

   Do not follow a fixed formula across different source scenarios. The combination of dimensions should be driven by what is most analytically interesting for the specific concept at hand.
4. **Formulate as Demanding but Accessible Questions:** The analytical challenge should be demanding enough for an expert, but the language should be clear enough that any educated adult can understand what is being asked. They must be genuinely open-ended, allowing for multiple valid analytical perspectives. The question should pose the analytical challenge directly — do not instruct the respondent on how to answer (e.g., avoid "In your answer, consider..." or "Discuss the role of..."). Ideally, a strong prompt will (a) invite engagement with established theoretical frameworks or empirical literatures, (b) surface genuine tensions or trade-offs rather than invite a single position, and (c) require reasoning that goes beyond common sense alone. Not every prompt needs to achieve all three, but every prompt must achieve (c).

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
[Identify the core social concept. Name the broader social mechanism. List 5 distinct analytical angles you will use, noting which diversity dimension(s) each varies on.]
</scratchpad>

<prompt_1>
  <diversity_dimensions>[Which dimensions this prompt varies on, e.g., "Legal/institutional analysis; systemic level; normative evaluation"]</diversity_dimensions>
  <underlying_issue>[A 5–15 word label naming the specific analytical angle]</underlying_issue>
  <question>[The full text of the open-ended essay question]</question>
</prompt_1>

(Repeat for <prompt_2> through <prompt_5>)
</instructions>

<input>
  <hle_question>
  {question}
  </hle_question>
  <hle_subject>
  {raw_subject}
  </hle_subject>
</input>
