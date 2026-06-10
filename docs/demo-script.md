# Demo Video Script: RegLoop AI

**Duration**: 3–5 Minutes  
**Target Audience**: Compliance Officers, Engineering Teams, and Regulatory Reviewers  

---

## Part 1: Introduction (0:00 - 0:45)

### Visuals
- Screen showing the RegLoop AI home/upload dashboard.
- A clean, modern dark-mode user interface with Outfit typography and glassmorphic panels.

### Narration
> "Welcome to RegLoop AI, a single-user prototype designed to streamline how compliance teams ingest regulatory updates, map them to internal policy frameworks, detect gaps, and generate reviewer pull requests with complete audit logs. 
>
> Today, we'll demonstrate a full compliance workflow starting from fresh regulatory documents to an exported compliance package."

---

## Part 2: Upload and Document Ingestion (0:45 - 1:30)

### Visuals
- Dragging and dropping the files from the `/samples` folder:
  1. `regulation.pdf` into the **Regulatory Update** slot.
  2. `compliance_monitoring_policy.pdf`, `incident_reporting_policy.pdf`, and `records_and_audit_policy.pdf` into the **Internal Policies** slot.
  3. `responsibility_matrix.csv` into the **Responsibility Matrix** slot.
- The interface updates with file sizes, counts, and shows the status as "Ready for Analysis" with the Analyze button activated.
- Clicking the **Run Ingestion & Analysis** button.

### Narration
> "We begin by uploading our workspace assets. We drag and drop one regulatory update PDF, three internal policy PDFs, and our responsibility matrix CSV mapping different domains to specific compliance owners.
> 
> As soon as the required inputs are validated, the readiness check passes, allowing us to kick off the ingestion and analysis run. In the backend, the system extracts text pages, segments policies into searchable chunks, and parses the owners' matrix."

---

## Part 3: Obligation Extraction & Policy Mapping (1:30 - 2:30)

### Visuals
- The screen transitions to show the **Obligations Table**.
- Pointing to columns: **Obligation Statement**, **Source Reference**, **Compliance Domain**, and **Extraction Confidence**.
- Clicking on a row to expand and view the **Policy Mapping Details**.
- Highlighting:
  - **Compliance Monitoring**: 75% match confidence mapping to `Compliance Monitoring Policy` (Status: Fully Covered).
  - **Incident Reporting**: 50% match confidence mapping to `Incident Reporting Policy` (Status: Partially Covered).
  - **Customer Disclosure**: 36% match confidence (Status: Not Covered / Ambiguous).
  - **Records Retention**: No match found (Status: Not Covered / Gap).

### Narration
> "Once the run completes, we are presented with five concrete regulatory obligations extracted directly from the update. For example, our Monitoring obligation has a high confidence score and references page 2 of the regulation.
> 
> When we dive into the policy mappings, we see that the system automatically matched our monitoring obligation with a 75% confidence score to the corresponding section of our Compliance Monitoring Policy, marking it as Fully Covered.
> 
> Meanwhile, the Incident Reporting obligation is matched with a 50% confidence score to our Incident Reporting Policy. Because the policy only addresses reporting 'material issues' rather than specific 'material incidents within 72 hours', it is flagged as Partially Covered."

---

## Part 4: Gap Analysis and Policy Pull Requests (2:30 - 3:30)

### Visuals
- Clicking on the **Policy Pull Requests (PRs)** tab.
- Highlighting the generated PRs:
  - Incident Reporting PR: shows proposed amendment (e.g. adding the 72 hours escalation window) and suggested owner "Jordan Lee" (derived from responsibility matrix).
  - Records Retention PR: shows proposed amendment for a 7-year retention policy and suggested owner "Morgan Patel".

### Narration
> "For the gaps identified, RegLoop AI generates Policy Pull Requests containing recommended amendments.
> 
> Looking at the Incident Reporting PR, the system recommends a specific wording change to incorporate the 72-hour window and automatically suggests 'Jordan Lee' as the owner, pulling their contact information directly from our uploaded matrix.
> 
> For the Records Retention obligation, which was completely unmapped, a new policy section is proposed to satisfy the 7-year retention rule, assigned to our Audit Lead, Morgan Patel."

---

## Part 5: Human Review, Audit Trail, and Export (3:30 - 5:00)

### Visuals
- Clicking on **Review Actions** for the Incident Reporting PR:
  - Choosing **Modify** and editing the text slightly.
  - Adding the comment: *"Adjusted wording to align with international standards."*
  - Clicking **Submit Review**. The status updates to `Modified`.
- Clicking on the **Audit Trail** timeline at the bottom of the workspace view, showing:
  - `document_uploaded`
  - `ingestion_run`
  - `gap_analysis_run`
  - `pr_reviewed` (highlighting the action, comment, and time).
- Clicking the **Export JSON** and **Export CSV** buttons in the header. Show the files downloading.

### Narration
> "Human reviewers have full control. We can Approve, Reject, Escalate, or Modify recommendations. 
> 
> Let's modify the Incident Reporting amendment, save our custom text, and submit. The system preserves our modification while retaining the original recommendation.
> 
> Every single workflow event is logged automatically in our immutable Audit Trail. We can see exactly when documents were uploaded, when the analyses ran, and who reviewed what.
> 
> Finally, we can download the full review package. By clicking Export JSON and Export CSV, we get a flattened compliance summary ready for regulatory audits and spreadsheet review. Thank you for watching!"
