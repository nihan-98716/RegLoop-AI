"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import styles from "./page.module.css";
import api from "@/lib/api";
import type { DocumentRead, DocumentType, WorkspaceDetailRead } from "@/lib/types";

const WORKSPACE_KEY = "regloop_workspace_id";

function formatBytes(bytes: number): string {
  if (bytes < 1_024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

export default function WorkspacePage() {
  const [workspace, setWorkspace] = useState<WorkspaceDetailRead | null>(null);
  const [initError, setInitError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<DocumentType | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);

  const regulationRef = useRef<HTMLInputElement>(null);
  const policyRef = useRef<HTMLInputElement>(null);
  const matrixRef = useRef<HTMLInputElement>(null);

  const loadWorkspace = useCallback(async (id: string) => {
    const ws = await api.workspace.get(id);
    setWorkspace(ws);
  }, []);

  // Initialise workspace on mount
  useEffect(() => {
    async function init() {
      const stored = localStorage.getItem(WORKSPACE_KEY);
      if (stored) {
        try {
          await loadWorkspace(stored);
          return;
        } catch {
          localStorage.removeItem(WORKSPACE_KEY);
        }
      }
      const created = await api.workspace.create();
      localStorage.setItem(WORKSPACE_KEY, created.id);
      await loadWorkspace(created.id);
    }
    init().catch((err) =>
      setInitError(err?.detail ?? "Failed to initialise workspace.")
    );
  }, [loadWorkspace]);

  async function handleUpload(file: File, type: DocumentType) {
    if (!workspace) return;
    setUploadError(null);
    setUploading(type);
    try {
      await api.workspace.uploadDocument(workspace.id, file, type);
      await loadWorkspace(workspace.id);
    } catch (err: any) {
      setUploadError(err?.detail ?? "Upload failed.");
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
    } catch (err: any) {
      setUploadError(err?.detail ?? "Remove failed.");
    } finally {
      setRemoving(null);
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

  return (
    <main className={styles.main}>
      <Nav onNew={newWorkspace} />

      {/* Header */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Upload workspace</h1>
        <p className={styles.pageMeta}>
          <code className={styles.wid}>{workspace.id.slice(0, 8)}</code>
          <span className={styles.sep}>·</span>
          <span>{workspace.name}</span>
        </p>
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
        <button
          className="btn btn-primary"
          disabled={!workspace.ready_for_analysis}
          id="btn-start-analysis"
          title={
            workspace.ready_for_analysis
              ? undefined
              : "Upload all required documents first"
          }
        >
          {workspace.ready_for_analysis
            ? "Start Analysis"
            : "Start Analysis — awaiting required inputs"}
        </button>
      </section>
    </main>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Nav({ onNew }: { onNew: () => void }) {
  return (
    <nav className={styles.nav}>
      <a href="/" className={styles.wordmark}>
        RegLoop AI
      </a>
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
