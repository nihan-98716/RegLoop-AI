import styles from "./page.module.css";

// ── Workflow data ────────────────────────────────────────────────────────────
const STEPS: [string, string, string][] = [
  ["01", "Upload",  "Regulatory PDF, policy documents, and responsibility matrix"],
  ["02", "Extract", "Structured obligations with citations and confidence scores"],
  ["03", "Map",     "Obligations matched to internal policy sections semantically"],
  ["04", "Analyse", "Coverage gaps rated High, Medium, or Low risk"],
  ["05", "Draft",   "Reviewable policy amendments with before and after diff"],
  ["06", "Review",  "Approve, reject, modify, or escalate each recommendation"],
  ["07", "Audit",   "Full traceability from regulation to reviewer decision"],
  ["08", "Export",  "JSON and CSV compliance review package"],
];

const FEATURES: [string, string][] = [
  ["Obligation extraction",  "LLM reads the regulatory document and returns structured obligations. Every item includes a source citation and a confidence score."],
  ["Policy mapping",         "Each obligation is compared semantically against your internal policy documents. Relevant sections and supporting excerpts are surfaced."],
  ["Gap analysis",           "The system determines whether each obligation is fully covered, partially covered, or not covered, and assigns a risk level."],
  ["Policy pull requests",   "For every gap, a reviewable amendment is generated with proposed change text, regulatory citation, and a suggested responsible owner."],
  ["Human review",           "Compliance officers approve, reject, modify, or escalate each AI recommendation. Decisions are persisted and linked to the audit trail."],
  ["Export",                 "The complete review package — obligations, mappings, gaps, amendments, decisions — is exportable as JSON or CSV."],
];

// ── SVG layout constants ─────────────────────────────────────────────────────
//
// ViewBox uses x: 0-100 (% units) and y: 0-FLOW_H (px units).
// preserveAspectRatio="none" stretches x to fill container width
// while y stays at FLOW_H px.
// vectorEffect="non-scaling-stroke" keeps stroke at exactly 1 screen-px.
//
const FLOW_H  = 680;   // container height in px
const LEFT_X  = 22;    // x position for left steps  (% of container width)
const RIGHT_X = 78;    // x position for right steps (% of container width)
const Y0      = 50;    // y of first step
const Y_GAP   = 82;    // vertical gap between steps

function stepY(i: number) {
  return Y0 + i * Y_GAP;
}

function buildPath(): string {
  // Single continuous cubic-bezier S-curve through all 8 step nodes
  const pts = STEPS.map((_, i) => ({
    x: i % 2 === 0 ? LEFT_X : RIGHT_X,
    y: stepY(i),
  }));
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length; i++) {
    const a = pts.at(i - 1)!;
    const b = pts.at(i)!;
    const mid = (a.y + b.y) / 2;
    // Cubic bezier: tangent stays vertical at both ends, crosses in the middle
    d += ` C ${a.x},${mid} ${b.x},${mid} ${b.x},${b.y}`;
  }
  return d;
}

// ── Page ─────────────────────────────────────────────────────────────────────
// nosemgrep: typescript.react.portability.i18next.jsx-not-internationalized.jsx-not-internationalized
export default function HomePage() {
  const pathD = buildPath();

  return (
    <main className={styles.main}>

      {/* Nav */}
      <nav className={styles.nav}>
        <span className={styles.wordmark}>RegLoop AI</span>
        <div className={styles.navRight}>
          <span className={styles.tag}>v1.0 · MVP</span>
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

      {/* Hero */}
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Compliance automation</p>
        <h1 className={styles.title}>
          Regulatory change to<br />review package in minutes.
        </h1>
        <p className={styles.subtitle}>
          Upload a regulatory update and your internal policies.
          RegLoop AI extracts obligations, maps your coverage,
          detects gaps, and generates reviewable policy amendments
          — with a complete audit trail.
        </p>
        <div className={styles.actions}>
          <a href="/workspace" className="btn btn-primary" id="cta-start">
            Start review
          </a>
          <a
            href="http://localhost:8000/api/health"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
            id="cta-health"
          >
            Health check
          </a>
        </div>
      </section>

      <div className={styles.divider} />

      {/* Workflow */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Workflow</p>

        {/* Flow container: SVG path behind, labels on top */}
        <div className={styles.flow} style={{ height: FLOW_H }}>

          <svg
            className={styles.flowSvg}
            viewBox={`0 0 100 ${FLOW_H}`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              d={pathD}
              stroke="#252525"
              strokeWidth="1"
              fill="none"
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          {STEPS.map(([num, name, desc], i) => {
            const isLeft = i % 2 === 0;
            const centerY = stepY(i);
            return (
              <div
                key={num}
                className={`${styles.flowStep} ${isLeft ? styles.stepLeft : styles.stepRight}`}
                style={{ top: centerY - 28 }}
              >
                <span className={styles.flowNum}>{num}</span>
                <div className={styles.flowContent}>
                  <p className={styles.flowName}>{name}</p>
                  <p className={styles.flowDesc}>{desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className={styles.divider} />

      {/* Capabilities */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Capabilities</p>
        <div className={styles.featureGrid}>
          {FEATURES.map(([title, desc]) => (
            <div key={title} className={styles.featureItem}>
              <p className={styles.featureTitle}>{title}</p>
              <p className={styles.featureDesc}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <span>RegLoop AI — single-user prototype</span>
        <span>Closed-Loop MVP · No authentication required</span>
      </footer>

    </main>
  );
}
