# AI Workflow

## Provider Strategy

Use a small provider abstraction so the application can call remote endpoints, Claude, or Gemini without changing workflow code.

Required provider behavior:

- Accept system prompt, user prompt, and structured output schema.
- Return raw text and parsed JSON.
- Capture model name and token metadata if available.
- Raise typed errors for provider failure, invalid JSON, or schema mismatch.

## Structured Output Rule

Every AI step must produce JSON that is validated before persistence. Do not persist free-form model output directly as authoritative data.

## Step 1: Obligation Extraction

Input:

- Regulatory document chunks

Output:

- Obligation statement
- Source citation/reference
- Source excerpt
- Confidence score
- Optional compliance domain

Prompt intent:

- Extract concrete duties, requirements, prohibitions, reporting expectations, control expectations, and review obligations.
- Avoid generic summaries.
- Preserve source references.

## Step 2: Policy Mapping

Input:

- One obligation
- Candidate policy chunks

Output:

- Relevant policy section or no-match result
- Matching excerpt
- Mapping rationale
- Confidence score

Prompt intent:

- Compare meaning, not only keywords.
- Prefer exact policy sections when available.
- Mark low confidence honestly.

## Step 3: Gap Analysis

Input:

- Obligation
- Mapped policy excerpt and rationale

Output:

- Coverage status: Fully Covered, Partially Covered, Not Covered
- Gap reasoning
- Risk level: High, Medium, Low
- Confidence score
- Source citations

Prompt intent:

- Decide whether the internal policy satisfies the regulatory obligation.
- Explain missing details, ambiguity, or control weaknesses.
- Assign risk based on compliance impact and policy coverage.

## Step 4: Policy Pull Request Generation

Input:

- Obligation
- Gap analysis
- Policy excerpt
- Responsibility owner candidates

Output:

- Gap description
- Proposed amendment
- Regulatory citation
- Suggested owner
- Risk level
- Confidence score
- Before text
- After text

Prompt intent:

- Generate reviewable recommendations.
- Never claim the amendment is final or approved.
- Keep amendments specific enough for a compliance officer to evaluate.

## Guardrails

- Show confidence scores and citations in the UI.
- Preserve original AI output after human modification.
- Treat missing citation as a validation warning or failed result.
- Use conservative phrasing for uncertain recommendations.
- Never automatically approve policy changes.

## Evaluation Notes

For sample data, create expected outputs for at least:

- One fully covered obligation
- One partially covered obligation
- One not covered obligation
- One high-risk policy PR
- One modified human review decision
