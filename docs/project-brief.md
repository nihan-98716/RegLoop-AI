# Project Brief

## Challenge Overview

Financial institutions spend significant manual effort whenever a new regulation is introduced. Compliance teams must read regulatory updates, identify obligations, compare them against internal policies, detect gaps, propose policy updates, and maintain an audit trail.

RegLoop AI should demonstrate how AI can transform:

`Regulatory Document -> Obligation Extraction -> Policy Mapping -> Gap Detection -> Policy Pull Request -> Human Review -> Audit Export`

The prototype is single-user and does not require authentication.

## Business Goal

Reduce the time required to prepare a regulatory compliance review package from days to minutes.

## Required Outputs

- Extracted regulatory obligations
- Mapped policy sections
- Gap analysis
- Policy change recommendations
- Audit-ready traceability

## Functional Requirements

### FR-1 Upload Workspace

Users can upload:

- One regulatory update document as PDF
- One to three internal policy documents as PDF
- One responsibility matrix as CSV

The system validates files, displays uploaded document summaries, supports removal and replacement, and allows analysis only after all required inputs are present.

### FR-2 Obligation Extraction

The system analyzes the regulatory document and extracts structured obligations containing:

- Obligation statement
- Source citation or reference
- Confidence score
- Optional suggested compliance domain

### FR-3 Policy Mapping

The system compares extracted obligations against uploaded policies and identifies relevant policy sections using semantic understanding, preferably with LLM context.

Each mapping includes:

- Relevant policy section
- Supporting excerpt
- Mapping confidence

### FR-4 Gap Analysis

The system determines coverage for each obligation:

- Fully Covered
- Partially Covered
- Not Covered

Gaps include reasoning, source citations where applicable, and a risk rating of High, Medium, or Low.

### FR-5 Policy Pull Request Generator

For each gap, the system generates a reviewable policy amendment with:

- Gap description
- Proposed amendment
- Regulatory citation
- Suggested owner
- Risk level
- Confidence score
- Before and after comparison

### FR-6 Human Review Workflow

Users can approve, reject, modify, or escalate generated policy pull requests. Status and reviewer actions must be persisted.

### FR-7 Audit Memory

The audit trail must show end-to-end traceability:

- Regulatory source
- Extracted obligation
- Policy mapping
- Detected gap
- Proposed amendment
- Review decision
- Responsible owner
- Timestamp

### FR-8 Export

The system exports the compliance review package as JSON and CSV, including all generated workflow artifacts.

## Expected Deliverables

- Source code
- Setup instructions
- Sample data
- Demo video, 3 to 5 minutes
- Architecture diagram
- README
