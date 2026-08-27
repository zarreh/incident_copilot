import type { IncidentReport } from "@/lib/types";

const SEVERITY_STYLES: Record<string, string> = {
  low: "#e6f4ea",
  medium: "#fff3cd",
  high: "#fde2e1",
  critical: "#f8d7da",
};

export function ReportPanel({ report }: { report: IncidentReport }) {
  const severityColor = SEVERITY_STYLES[report.severity.toLowerCase()] ?? "#eee";
  const evidence = report.evidence ?? [];
  const recommendedActions = report.recommended_actions ?? [];

  return (
    <section
      aria-label="Incident report"
      style={{
        border: "1px solid #ddd",
        borderRadius: "8px",
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{report.title}</h2>
        <span
          style={{
            background: severityColor,
            borderRadius: "4px",
            padding: "0.15rem 0.5rem",
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
          }}
        >
          {report.severity}
        </span>
      </div>

      {report.insufficient_evidence && (
        <p
          role="status"
          style={{
            background: "#fde2e1",
            color: "#7a1f1f",
            borderRadius: "4px",
            padding: "0.5rem",
            fontSize: "0.875rem",
            margin: 0,
          }}
        >
          Insufficient evidence: the gathered evidence does not support a confident
          root cause. This is a deliberate refusal to guess, not a failed run.
        </p>
      )}

      <p style={{ margin: 0 }}>{report.root_cause}</p>

      <div style={{ fontSize: "0.8rem", color: "#666" }}>
        Confidence: {(report.confidence * 100).toFixed(0)}%
      </div>

      {evidence.length > 0 && (
        <div>
          <h3 style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "#666" }}>
            Evidence
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
            {evidence.map((e, i) => (
              <li key={i}>
                {e.detail}{" "}
                <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#999" }}>
                  ({e.source}: {e.reference})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {recommendedActions.length > 0 && (
        <div>
          <h3 style={{ fontSize: "0.75rem", textTransform: "uppercase", color: "#666" }}>
            Recommended actions
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
            {recommendedActions.map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
