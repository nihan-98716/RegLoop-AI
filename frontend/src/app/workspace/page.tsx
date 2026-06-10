"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useCallback } from "react";
import styles from "./page.module.css";
import api from "@/lib/api";
import type {
  DocumentRead,
  DocumentType,
  GapAnalysisRead,
  IngestionStatusRead,
  ObligationRead,
  PolicyMappingRead,
  PolicyPullRequestRead,
  ResponsibilityOwnerRead,
  WorkspaceDetailRead,
} from "@/lib/types";

const WORKSPACE_KEY = "regloop_workspace_id";

function formatBytes(bytes: number): string {
  if (bytes < 1_024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

function errorDetail(err: unknown, fallback: string): string {
  if (typeof err === "object" && err !== null && "detail" in err) {
    const detail = (err as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export default function WorkspacePage() {
  const [workspace, setWorkspace] = useState<WorkspaceDetailRead | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<DocumentType | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [ingestion, setIngestion] = useState<IngestionStatusRead | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [ingestionError, setIngestionError] = useState<string | null>(null);
  const [obligations, setObligations] = useState<ObligationRead[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [obligationError, setObligationError] = useState<string | null>(null);
  const [mappings, setMappings] = useState<PolicyMappingRead[]>([]);
  const [mapping, setMapping] = useState(false);
  const [mappingError, setMappingError] = useState<string | null>(null);
  const [gapAnalyses, setGapAnalyses] = useState<GapAnalysisRead[]>([]);
  const [analyzingGaps, setAnalyzingGaps] = useState(false);
  const [gapAnalysisError, setGapAnalysisError] = useState<string | null>(null);
  const [pullRequests, setPullRequests] = useState<PolicyPullRequestRead[]>([]);
  const [generatingPrs, setGeneratingPrs] = useState(false);
  const [prError, setPrError] = useState<string | null>(null);

  // Filters for PR list
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterOwner, setFilterOwner] = useState<string>("");
  const [filterRisk, setFilterRisk] = useState<string>("");

  // Review states inline per PR
  const [reviewComment, setReviewComment] = useState<{ [id: string]: string }>({});
  const [reviewLabel, setReviewLabel] = useState<{ [id: string]: string }>({});
  const [reviewModifiedText, setReviewModifiedText] = useState<{ [id: string]: string }>({});
  const [reviewAction, setReviewAction] = useState<{ [id: string]: string }>({});
  const [submittingReview, setSubmittingReview] = useState<{ [id: string]: boolean }>({});

  const regulationRef = useRef<HTMLInputElement>(null);
  const policyRef = useRef<HTMLInputElement>(null);
  const matrixRef = useRef<HTMLInputElement>(null);

  const loadWorkspace = useCallback(async (id: string) => {
    const ws = await api.workspace.get(id);
    setWorkspace(ws);
  }, []);

  const loadIngestion = useCallback(async (id: string) => {
    const status = await api.workspace.getIngestion(id);
    setIngestion(status);
  }, []);

  const loadObligations = useCallback(async (id: string) => {
    const items = await api.workspace.listObligations(id);
    setObligations(items);
  }, []);

  const loadMappings = useCallback(async (id: string) => {
    const items = await api.workspace.listMappings(id);
    setMappings(items);
  }, []);

  const loadGapAnalyses = useCallback(async (id: string) => {
    const items = await api.workspace.listGapAnalyses(id);
    setGapAnalyses(items);
  }, []);

  const loadPullRequests = useCallback(async (id: string, filters?: { status?: string; owner_id?: string; risk_level?: string }) => {
    const items = await api.workspace.listPolicyPullRequests(id, filters);
    setPullRequests(items);
  }, []);

  // Reload PRs when filters change
  useEffect(() => {
    if (workspace) {
      loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      }).catch((err) => setPrError(errorDetail(err, "Failed to load pull requests.")));
    }
  }, [workspace, filterStatus, filterOwner, filterRisk, loadPullRequests]);

  // Initialise workspace on mount
  useEffect(() => {
    async function init() {
      const stored = localStorage.getItem(WORKSPACE_KEY);
      if (stored) {
        try {
          await loadWorkspace(stored);
          await loadIngestion(stored);
          await loadObligations(stored);
          await loadMappings(stored);
          await loadGapAnalyses(stored);
          await loadPullRequests(stored);
          return;
        } catch {
          localStorage.removeItem(WORKSPACE_KEY);
        }
      }
      const created = await api.workspace.create();
      localStorage.setItem(WORKSPACE_KEY, created.id);
      await loadWorkspace(created.id);
      await loadIngestion(created.id);
      await loadObligations(created.id);
      await loadMappings(created.id);
      await loadGapAnalyses(created.id);
      await loadPullRequests(created.id);
    }
    init().catch((err) =>
      setInitError(err?.detail ?? "Failed to initialise workspace.")
    );
  }, [loadWorkspace, loadIngestion, loadObligations, loadMappings, loadGapAnalyses, loadPullRequests]);

  async function handleUpload(file: File, type: DocumentType) {
    if (!workspace) return;
    setUploadError(null);
    setUploading(type);
    try {
      await api.workspace.uploadDocument(workspace.id, file, type);
      await loadWorkspace(workspace.id);
      await loadIngestion(workspace.id);
      await loadObligations(workspace.id);
      await loadMappings(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setUploadError(errorDetail(err, "Upload failed."));
    } finally {
      setUploading(null);
    }
  }

  async function handleRemove(docId: string) {
    if (!workspace) return;
    setUploadError(null);
    setRemoving(docId);
    try {
      await api.workspace.deleteDocument(workspace.id, docId);
      await loadWorkspace(workspace.id);
      await loadIngestion(workspace.id);
      await loadObligations(workspace.id);
      await loadMappings(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setUploadError(errorDetail(err, "Remove failed."));
    } finally {
      setRemoving(null);
    }
  }

  async function handleRunIngestion() {
    if (!workspace) return;
    setIngestionError(null);
    setIngesting(true);
    try {
      await api.workspace.runIngestion(workspace.id);
      await loadWorkspace(workspace.id);
      await loadIngestion(workspace.id);
      await loadObligations(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setIngestionError(errorDetail(err, "Ingestion failed."));
    } finally {
      setIngesting(false);
    }
  }

  async function handleExtractObligations() {
    if (!workspace) return;
    setObligationError(null);
    setExtracting(true);
    try {
      await api.workspace.extractObligations(workspace.id);
      await loadWorkspace(workspace.id);
      await loadObligations(workspace.id);
      await loadMappings(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setObligationError(errorDetail(err, "Obligation extraction failed."));
    } finally {
      setExtracting(false);
    }
  }

  async function handleRunMapping() {
    if (!workspace) return;
    setMappingError(null);
    setMapping(true);
    try {
      await api.workspace.runMapping(workspace.id);
      await loadMappings(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setMappingError(errorDetail(err, "Policy mapping failed."));
    } finally {
      setMapping(false);
    }
  }

  async function handleRunGapAnalysis() {
    if (!workspace) return;
    setGapAnalysisError(null);
    setAnalyzingGaps(true);
    try {
      await api.workspace.runGapAnalysis(workspace.id);
      await loadGapAnalyses(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setGapAnalysisError(errorDetail(err, "Gap analysis failed."));
    } finally {
      setAnalyzingGaps(false);
    }
  }

  async function handleRunPolicyPullRequests() {
    if (!workspace) return;
    setPrError(null);
    setGeneratingPrs(true);
    try {
      await api.workspace.runPolicyPullRequests(workspace.id);
      await loadPullRequests(workspace.id, {
        status: filterStatus || undefined,
        owner_id: filterOwner || undefined,
        risk_level: filterRisk || undefined,
      });
    } catch (err: unknown) {
      setPrError(errorDetail(err, "Failed to generate policy pull requests."));
    } finally {
      setGeneratingPrs(false);
    }
  }

  async function handleSubmitReview(prId: string) {
    const action = reviewAction[prId] || "approve";
    const label = reviewLabel[prId] || "Compliance Officer";
    const comment = reviewComment[prId] || "";
    const modifiedText = reviewModifiedText[prId] || "";

    if (action === "modify" && !modifiedText.trim()) {
      alert("Please provide the modified text.");
      return;
    }

    setSubmittingReview((prev) => ({ ...prev, [prId]: true }));
    try {
      await api.reviewPullRequest(prId, {
        action,
        reviewer_label: label,
        comment: comment || null,
        modified_text: action === "modify" ? modifiedText : null,
      });
      // Clear review fields for this PR
      setReviewComment((prev) => ({ ...prev, [prId]: "" }));
      setReviewLabel((prev) => ({ ...prev, [prId]: "" }));
      setReviewModifiedText((prev) => ({ ...prev, [prId]: "" }));
      setReviewAction((prev) => ({ ...prev, [prId]: "" }));
      // Reload pull requests
      if (workspace) {
        await loadPullRequests(workspace.id, {
          status: filterStatus || undefined,
          owner_id: filterOwner || undefined,
          risk_level: filterRisk || undefined,
        });
      }
    } catch (err: unknown) {
      alert(errorDetail(err, "Failed to submit review."));
    } finally {
      setSubmittingReview((prev) => ({ ...prev, [prId]: false }));
    }
  }

  function newWorkspace() {
    localStorage.removeItem(WORKSPACE_KEY);
    window.location.reload();
  }

  const docs = workspace?.documents ?? [];
  const regulation = docs.find((d) => d.document_type === "regulation");
  const policies = docs.filter((d) => d.document_type === "policy");
  const matrix = docs.find((d) => d.document_type === "responsibility_matrix");

  // ── Render ──────────────────────────────────────────────────────────────

  if (initError) {
    return (
      <main className={styles.main}>
        <Nav onNew={newWorkspace} />
        <div className={styles.errorFull}>
          <p className={styles.errorTitle}>Failed to load workspace</p>
          <p className={styles.errorDetail}>{initError}</p>
          <button className="btn btn-ghost" onClick={newWorkspace}>
            Try again
          </button>
        </div>
      </main>
    );
  }

  if (!workspace) {
    return (
      <main className={styles.main}>
        <Nav onNew={newWorkspace} />
        <div className={styles.loading}>Initialising workspace...</div>
      </main>
    );
  }

  const exportJsonUrl = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/workspaces/${workspace.id}/export.json`;
  const exportCsvUrl = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/workspaces/${workspace.id}/export.csv`;

  return (
    <main className={styles.main}>
      <Nav onNew={newWorkspace} />

      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Upload workspace</h1>
          <p className={styles.pageMeta}>
            <code className={styles.wid}>{workspace.id.slice(0, 8)}</code>
            <span className={styles.sep}>·</span>
            <span>{workspace.name}</span>
          </p>
        </div>
        <div className={styles.headerActions}>
          <a
            href={exportJsonUrl}
            download
            className="btn btn-ghost"
            id="btn-export-json"
          >
            Export JSON
          </a>
          <a
            href={exportCsvUrl}
            download
            className="btn btn-ghost"
            id="btn-export-csv"
          >
            Export CSV
          </a>
        </div>
      </div>

      {/* Error banner */}
      {uploadError && (
        <div className={styles.errorBanner} id="upload-error-banner">
          <span>{uploadError}</span>
          <button
            className={styles.errorDismiss}
            onClick={() => setUploadError(null)}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {ingestionError && (
        <div className={styles.errorBanner} id="ingestion-error-banner">
          <span>{ingestionError}</span>
          <button
            className={styles.errorDismiss}
            onClick={() => setIngestionError(null)}
            aria-label="Dismiss ingestion error"
          >
            ×
          </button>
        </div>
      )}

      {obligationError && (
        <div className={styles.errorBanner} id="obligation-error-banner">
          <span>{obligationError}</span>
          <button
            className={styles.errorDismiss}
            onClick={() => setObligationError(null)}
            aria-label="Dismiss obligation error"
          >
            ×
          </button>
        </div>
      )}

      {/* ── Regulation ── */}
      <section className={styles.section}>
        <SectionHeader
          label="Regulation"
          hint="One regulatory update PDF required"
        />
        {regulation ? (
          <FileRow
            doc={regulation}
            onRemove={() => handleRemove(regulation.id)}
            isRemoving={removing === regulation.id}
          />
        ) : (
          <EmptyRow
            label="No file uploaded"
            action={
              <UploadButton
                id="btn-upload-regulation"
                label="Upload PDF"
                loading={uploading === "regulation"}
                disabled={!!uploading}
                onClick={() => regulationRef.current?.click()}
              />
            }
          />
        )}
        <input
          ref={regulationRef}
          type="file"
          accept=".pdf,application/pdf"
          className={styles.hiddenInput}
          id="input-regulation"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleUpload(f, "regulation");
            e.target.value = "";
          }}
        />
      </section>

      {/* ── Policy Documents ── */}
      <section className={styles.section}>
        <SectionHeader
          label="Policy Documents"
          hint={`${policies.length}/3 uploaded · 1-3 internal policy PDFs required`}
        />
        {policies.length === 0 ? (
          <EmptyRow
            label="No files uploaded"
            action={
              <UploadButton
                id="btn-upload-policy"
                label="Add Policy PDF"
                loading={uploading === "policy"}
                disabled={!!uploading}
                onClick={() => policyRef.current?.click()}
              />
            }
          />
        ) : (
          <>
            {policies.map((doc) => (
              <FileRow
                key={doc.id}
                doc={doc}
                onRemove={() => handleRemove(doc.id)}
                isRemoving={removing === doc.id}
              />
            ))}
            {policies.length < 3 && (
              <div className={styles.addMoreRow}>
                <UploadButton
                  id="btn-upload-policy-more"
                  label={`Add another (${policies.length} / 3)`}
                  loading={uploading === "policy"}
                  disabled={!!uploading}
                  onClick={() => policyRef.current?.click()}
                />
              </div>
            )}
          </>
        )}
        <input
          ref={policyRef}
          type="file"
          accept=".pdf,application/pdf"
          className={styles.hiddenInput}
          id="input-policy"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleUpload(f, "policy");
            e.target.value = "";
          }}
        />
      </section>

      {/* ── Responsibility Matrix ── */}
      <section className={styles.section}>
        <SectionHeader
          label="Responsibility Matrix"
          hint="One CSV required · columns: domain, policy_area, owner_name, owner_role, owner_email, notes"
        />
        {matrix ? (
          <FileRow
            doc={matrix}
            onRemove={() => handleRemove(matrix.id)}
            isRemoving={removing === matrix.id}
          />
        ) : (
          <EmptyRow
            label="No file uploaded"
            action={
              <UploadButton
                id="btn-upload-matrix"
                label="Upload CSV"
                loading={uploading === "responsibility_matrix"}
                disabled={!!uploading}
                onClick={() => matrixRef.current?.click()}
              />
            }
          />
        )}
        <input
          ref={matrixRef}
          type="file"
          accept=".csv,text/csv"
          className={styles.hiddenInput}
          id="input-matrix"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleUpload(f, "responsibility_matrix");
            e.target.value = "";
          }}
        />
      </section>

      {/* ── Readiness ── */}
      <section className={styles.readinessSection}>
        <div className={styles.readinessList}>
          <ReadinessItem label="Regulation PDF" met={!!regulation} />
          <ReadinessItem
            label={`Policy document (${policies.length} / 3)`}
            met={policies.length >= 1}
          />
          <ReadinessItem label="Responsibility matrix" met={!!matrix} />
        </div>
        <div className={styles.actionRow}>
          <button
            className="btn btn-primary"
            disabled={!workspace.ready_for_analysis || ingesting}
            id="btn-run-ingestion"
            title={
              workspace.ready_for_analysis
                ? undefined
                : "Upload all required documents first"
            }
            onClick={handleRunIngestion}
          >
            {ingesting
              ? "Ingesting..."
              : workspace.ready_for_analysis
                ? "Run Ingestion"
                : "Run Ingestion — awaiting required inputs"}
          </button>
        </div>
      </section>

      <section className={styles.ingestionSection}>
        <SectionHeader
          label="Ingestion Status"
          hint="Normalized text chunks and responsibility owners"
        />
        <div className={styles.metricsGrid}>
          <Metric label="Status" value={ingestion?.status ?? workspace.status} />
          <Metric label="Text Chunks" value={`${ingestion?.chunks.length ?? 0}`} />
          <Metric
            label="Owners"
            value={`${ingestion?.responsibility_owners.length ?? 0}`}
          />
        </div>
        {!!ingestion?.chunks.length && (
          <div className={styles.previewList}>
            {ingestion.chunks.slice(0, 3).map((chunk) => (
              <div className={styles.previewItem} key={chunk.id}>
                <span className={styles.previewMeta}>
                  Page {chunk.page_number ?? "?"}
                  {chunk.section_label ? ` · ${chunk.section_label}` : ""}
                </span>
                <p className={styles.previewText}>{chunk.text}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className={styles.obligationSection}>
        <SectionHeader
          label="Obligations"
          hint="Structured regulatory obligations with source references and confidence"
        />
        <div className={styles.actionRow}>
          <button
            className="btn btn-primary"
            disabled={!ingestion?.chunks.length || extracting}
            id="btn-extract-obligations"
            title={
              ingestion?.chunks.length
                ? undefined
                : "Run ingestion before extracting obligations"
            }
            onClick={handleExtractObligations}
          >
            {extracting
              ? "Extracting..."
              : ingestion?.chunks.length
                ? "Extract Obligations"
                : "Extract Obligations — awaiting ingestion"}
          </button>
        </div>
        {obligations.length > 0 ? (
          <div className={styles.obligationTable}>
            {obligations.map((item) => (
              <div className={styles.obligationRow} key={item.id}>
                <div className={styles.obligationStatement}>{item.statement}</div>
                <div className={styles.obligationMeta}>
                  <span>{item.source_reference}</span>
                  <span>{item.confidence}% confidence</span>
                  {item.compliance_domain && <span>{item.compliance_domain}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>No obligations extracted yet</div>
        )}
      </section>

      <section className={styles.obligationSection}>
        <SectionHeader
          label="Policy Mapping"
          hint="Each obligation mapped to the best matching policy section"
        />
        {mappingError && (
          <div className={styles.errorBanner} id="mapping-error-banner">
            <span>{mappingError}</span>
            <button
              className={styles.errorDismiss}
              onClick={() => setMappingError(null)}
              aria-label="Dismiss mapping error"
            >
              ×
            </button>
          </div>
        )}
        <div className={styles.actionRow}>
          <button
            className="btn btn-primary"
            disabled={obligations.length === 0 || mapping}
            id="btn-run-mapping"
            title={obligations.length === 0 ? "Extract obligations before running mapping" : undefined}
            onClick={handleRunMapping}
          >
            {mapping
              ? "Mapping..."
              : obligations.length > 0
                ? "Run Policy Mapping"
                : "Run Policy Mapping — awaiting obligations"}
          </button>
        </div>
        {mappings.length > 0 ? (
          <div className={styles.obligationTable}>
            {mappings.map((m) => (
              <div
                key={m.id}
                className={`${styles.obligationRow} ${m.is_no_match ? styles.noMatchRow : ""}`}
                id={`mapping-row-${m.id}`}
              >
                <div className={styles.obligationMeta}>
                  {m.is_no_match ? (
                    <span className={styles.noMatchBadge}>NO MATCH</span>
                  ) : (
                    <span className={styles.matchBadge}>MATCHED</span>
                  )}
                  <span>{m.confidence}% confidence</span>
                </div>
                <div className={styles.obligationStatement}>
                  {m.mapping_rationale}
                </div>
                {m.policy_excerpt && (
                  <blockquote className={styles.policyExcerpt}>
                    {m.policy_excerpt}
                  </blockquote>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>No mappings run yet</div>
        )}
      </section>

      <section className={styles.obligationSection}>
        <SectionHeader
          label="Gap Analysis"
          hint="Assess coverage status and compliance risk for each obligation"
        />
        {gapAnalysisError && (
          <div className={styles.errorBanner} id="gap-analysis-error-banner">
            <span>{gapAnalysisError}</span>
            <button
              className={styles.errorDismiss}
              onClick={() => setGapAnalysisError(null)}
              aria-label="Dismiss gap analysis error"
            >
              ×
            </button>
          </div>
        )}
        <div className={styles.actionRow}>
          <button
            className="btn btn-primary"
            disabled={mappings.length === 0 || analyzingGaps}
            id="btn-run-gap-analysis"
            title={mappings.length === 0 ? "Run policy mapping before running gap analysis" : undefined}
            onClick={handleRunGapAnalysis}
          >
            {analyzingGaps
              ? "Analyzing..."
              : mappings.length > 0
                ? "Run Gap Analysis"
                : "Run Gap Analysis — awaiting policy mappings"}
          </button>
        </div>
        {gapAnalyses.length > 0 ? (
          <div className={styles.obligationTable}>
            {gapAnalyses.map((g) => {
              let rowClass = "";
              let statusBadgeClass = "";
              let statusText = "";
              if (g.coverage_status === "fully_covered") {
                rowClass = styles.fullyCoveredRow;
                statusBadgeClass = styles.fullyCoveredBadge;
                statusText = "FULLY COVERED";
              } else if (g.coverage_status === "partially_covered") {
                rowClass = styles.partiallyCoveredRow;
                statusBadgeClass = styles.partiallyCoveredBadge;
                statusText = "PARTIALLY COVERED";
              } else {
                rowClass = styles.notCoveredRow;
                statusBadgeClass = styles.notCoveredBadge;
                statusText = "NOT COVERED";
              }

              let riskBadgeClass = `${styles.riskBadge}`;
              if (g.risk_level === "high") {
                riskBadgeClass += ` ${styles.riskHigh}`;
              } else if (g.risk_level === "medium") {
                riskBadgeClass += ` ${styles.riskMedium}`;
              } else {
                riskBadgeClass += ` ${styles.riskLow}`;
              }

              return (
                <div
                  key={g.id}
                  className={`${styles.obligationRow} ${rowClass}`}
                  id={`gap-row-${g.id}`}
                >
                  <div className={styles.obligationMeta}>
                    <span className={statusBadgeClass}>{statusText}</span>
                    <span className={riskBadgeClass}>{g.risk_level.toUpperCase()} RISK</span>
                    <span>{g.confidence}% confidence</span>
                  </div>
                  <div className={styles.obligationStatement}>
                    {g.reasoning}
                  </div>
                  {g.source_citations && (
                    <div className={styles.citationsBlock}>
                      <strong>Citations:</strong> {g.source_citations}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className={styles.emptyState}>No gap analysis run yet</div>
        )}
      </section>

      <section className={styles.obligationSection}>
        <SectionHeader
          label="Policy Pull Requests"
          hint="AI-generated policy amendments and compliance before-and-after reviews"
        />
        {prError && (
          <div className={styles.errorBanner} id="pr-error-banner">
            <span>{prError}</span>
            <button
              className={styles.errorDismiss}
              onClick={() => setPrError(null)}
              aria-label="Dismiss PR error"
            >
              ×
            </button>
          </div>
        )}

        {/* PR Control & Filtering Bar */}
        <div className={styles.filterBar}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Status:</label>
            <select
              className={styles.filterSelect}
              id="select-filter-status"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="modified">Modified</option>
              <option value="escalated">Escalated</option>
            </select>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Suggested Owner:</label>
            <select
              className={styles.filterSelect}
              id="select-filter-owner"
              value={filterOwner}
              onChange={(e) => setFilterOwner(e.target.value)}
            >
              <option value="">All Owners</option>
              {ingestion?.responsibility_owners.map((owner) => (
                <option key={owner.id} value={owner.id}>
                  {owner.owner_name} ({owner.domain})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>Risk Level:</label>
            <select
              className={styles.filterSelect}
              id="select-filter-risk"
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value)}
            >
              <option value="">All Risks</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
            </select>
          </div>
        </div>

        <div className={styles.actionRow} style={{ marginTop: "1rem" }}>
          <button
            className="btn btn-primary"
            disabled={gapAnalyses.length === 0 || generatingPrs}
            id="btn-generate-prs"
            title={gapAnalyses.length === 0 ? "Run gap analysis before generating policy PRs" : undefined}
            onClick={handleRunPolicyPullRequests}
          >
            {generatingPrs
              ? "Generating..."
              : gapAnalyses.length > 0
                ? "Generate Policy PRs"
                : "Generate Policy PRs — awaiting gap analysis"}
          </button>
        </div>

        {pullRequests.length > 0 ? (
          <div className={styles.obligationTable}>
            {pullRequests.map((pr) => {
              let prStatusBadgeClass = styles.matchBadge;
              if (pr.status === "approved") prStatusBadgeClass = styles.fullyCoveredBadge;
              else if (pr.status === "rejected" || pr.status === "escalated") prStatusBadgeClass = styles.notCoveredBadge;
              else if (pr.status === "modified") prStatusBadgeClass = styles.partiallyCoveredBadge;

              let riskBadgeClass = `${styles.riskBadge}`;
              if (pr.risk_level === "high") {
                riskBadgeClass += ` ${styles.riskHigh}`;
              } else if (pr.risk_level === "medium") {
                riskBadgeClass += ` ${styles.riskMedium}`;
              } else {
                riskBadgeClass += ` ${styles.riskLow}`;
              }

              const selectedAction = reviewAction[pr.id] || "approve";

              return (
                <div
                  key={pr.id}
                  className={styles.prCard}
                  id={`pr-card-${pr.id}`}
                >
                  <div className={styles.prHeader}>
                    <h3 className={styles.prTitle}>{pr.title}</h3>
                    <div className={styles.obligationMeta} style={{ margin: 0 }}>
                      <span className={prStatusBadgeClass}>{pr.status.toUpperCase()}</span>
                      <span className={riskBadgeClass}>{pr.risk_level.toUpperCase()} RISK</span>
                      <span>{pr.confidence}% confidence</span>
                    </div>
                  </div>

                  <p className={styles.gapDescription}>
                    <strong>Detected Gap:</strong> {pr.gap_description}
                  </p>

                  <div className={styles.metaRow}>
                    {pr.regulatory_citation && (
                      <span>
                        <strong>Regulation Citation:</strong> {pr.regulatory_citation}
                      </span>
                    )}
                    {pr.suggested_owner && (
                      <span>
                        <strong>Suggested Owner:</strong> {pr.suggested_owner.owner_name} ({pr.suggested_owner.owner_role ?? "Owner"}, {pr.suggested_owner.owner_email})
                      </span>
                    )}
                  </div>

                  {/* Before & After Diff Blocks */}
                  <div className={styles.diffContainer}>
                    <div className={`${styles.diffBlock} ${styles.diffBefore}`}>
                      <h4 className={styles.diffHeader}>Before (Current Policy Excerpt)</h4>
                      <pre className={styles.diffText}>
                        {pr.before_text || "[No matching policy excerpt - New Addition]"}
                      </pre>
                    </div>
                    <div className={`${styles.diffBlock} ${styles.diffAfter}`}>
                      <h4 className={styles.diffHeader}>After (Amended Policy)</h4>
                      <pre className={styles.diffText}>{pr.after_text}</pre>
                    </div>
                  </div>

                  {/* Existing Review Actions Timeline */}
                  {pr.review_actions && pr.review_actions.length > 0 && (
                    <div className={styles.timeline}>
                      <h4 className={styles.timelineTitle}>Review Audit History</h4>
                      {pr.review_actions.map((act) => (
                        <div key={act.id} className={styles.timelineItem}>
                          <span className={styles.timelineAction}>
                            {act.action.toUpperCase()}
                          </span>
                          <span className={styles.timelineMeta}>
                            by {act.reviewer_label} on {new Date(act.created_at).toLocaleDateString()}
                          </span>
                          {act.comment && (
                            <p className={styles.timelineComment}>
                              Comment: "{act.comment}"
                            </p>
                          )}
                          {act.modified_text && (
                            <pre className={styles.timelineModifiedText}>
                              Modified Text: "{act.modified_text}"
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Inline Review Action Form */}
                  <div className={styles.reviewForm} id={`review-form-${pr.id}`}>
                    <h4 className={styles.reviewFormTitle}>Submit Compliance Review</h4>
                    <div className={styles.reviewFields}>
                      <div className={styles.reviewInputGroup}>
                        <label className={styles.filterLabel}>Action:</label>
                        <select
                          className={styles.filterSelect}
                          value={selectedAction}
                          onChange={(e) => setReviewAction(prev => ({ ...prev, [pr.id]: e.target.value }))}
                        >
                          <option value="approve">Approve</option>
                          <option value="reject">Reject</option>
                          <option value="modify">Modify (Edit Text)</option>
                          <option value="escalate">Escalate</option>
                        </select>
                      </div>

                      <div className={styles.reviewInputGroup}>
                        <label className={styles.filterLabel}>Reviewer Label:</label>
                        <input
                          type="text"
                          className={styles.reviewerInput}
                          placeholder="Compliance Officer"
                          value={reviewLabel[pr.id] ?? ""}
                          onChange={(e) => setReviewLabel(prev => ({ ...prev, [pr.id]: e.target.value }))}
                        />
                      </div>
                    </div>

                    {selectedAction === "modify" && (
                      <div className={styles.reviewInputGroup} style={{ marginTop: "1rem" }}>
                        <label className={styles.filterLabel}>Modify Policy Amendment:</label>
                        <textarea
                          className={styles.reviewerTextarea}
                          value={reviewModifiedText[pr.id] ?? pr.after_text}
                          onChange={(e) => setReviewModifiedText(prev => ({ ...prev, [pr.id]: e.target.value }))}
                        />
                      </div>
                    )}

                    <div className={styles.reviewInputGroup} style={{ marginTop: "1rem" }}>
                      <label className={styles.filterLabel}>Comment:</label>
                      <input
                        type="text"
                        className={styles.reviewerCommentInput}
                        placeholder="Add review notes..."
                        value={reviewComment[pr.id] ?? ""}
                        onChange={(e) => setReviewComment(prev => ({ ...prev, [pr.id]: e.target.value }))}
                      />
                    </div>

                    <button
                      className="btn btn-ghost"
                      style={{ marginTop: "1rem" }}
                      disabled={submittingReview[pr.id]}
                      onClick={() => handleSubmitReview(pr.id)}
                    >
                      {submittingReview[pr.id] ? "Submitting..." : "Submit Review Action"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className={styles.emptyState}>No pull requests generated yet</div>
        )}
      </section>
    </main>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Nav({ onNew }: { onNew: () => void }) {
  return (
    <nav className={styles.nav}>
      <Link href="/" className={styles.wordmark}>
        RegLoop AI
      </Link>
      <div className={styles.navRight}>
        <button
          className="btn btn-ghost"
          onClick={onNew}
          id="btn-new-workspace"
        >
          New workspace
        </button>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-ghost"
          id="nav-api-docs"
        >
          API docs
        </a>
      </div>
    </nav>
  );
}

function SectionHeader({ label, hint }: { label: string; hint: string }) {
  return (
    <div className={styles.sectionHeader}>
      <p className={styles.sectionLabel}>{label}</p>
      <p className={styles.sectionHint}>{hint}</p>
    </div>
  );
}

function EmptyRow({
  label,
  action,
}: {
  label: string;
  action: React.ReactNode;
}) {
  return (
    <div className={styles.emptyRow}>
      <span className={styles.emptyText}>{label}</span>
      {action}
    </div>
  );
}

function FileRow({
  doc,
  onRemove,
  isRemoving,
}: {
  doc: DocumentRead;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  return (
    <div className={styles.fileRow} id={`file-row-${doc.id}`}>
      <div className={styles.fileInfo}>
        <span className={styles.fileName}>{doc.original_filename}</span>
        <span className={styles.fileMeta}>
          {formatBytes(doc.size_bytes)}
          <span className={styles.metaSep}>·</span>
          <code className={styles.checksum}>{doc.checksum.slice(0, 12)}...</code>
        </span>
      </div>
      <button
        className={`btn btn-ghost ${styles.removeBtn}`}
        onClick={onRemove}
        disabled={isRemoving}
        id={`btn-remove-${doc.id}`}
      >
        {isRemoving ? "Removing..." : "Remove"}
      </button>
    </div>
  );
}

function UploadButton({
  id,
  label,
  loading,
  disabled,
  onClick,
}: {
  id: string;
  label: string;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      id={id}
      className="btn btn-ghost"
      onClick={onClick}
      disabled={disabled}
    >
      {loading ? "Uploading..." : label}
    </button>
  );
}

function ReadinessItem({ label, met }: { label: string; met: boolean }) {
  return (
    <div className={`${styles.readinessItem} ${met ? styles.met : ""}`}>
      <span className={styles.readinessDot} />
      <span>{label}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue}>{value}</span>
    </div>
  );
}
