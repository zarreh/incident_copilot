import type { TraceEvent } from "@/lib/types";

// Node filename == node name == span name. These labels are the human-facing
// names for each node in oncall.graph (agent -> tools -> agent* -> summarize -> verify).
const NODE_LABELS: Record<string, string> = {
  agent: "Investigating (searching logs, checking known issues)",
  tools: "Running a tool call",
  summarize: "Drafting the incident report",
  verify: "Checking every citation against the evidence gathered",
};

export function TraceTimeline({ events }: { events: TraceEvent[] }) {
  // __end__ is a stream-termination marker, not a graph step.
  const steps = events.filter((event) => event.node !== "__end__");
  if (steps.length === 0) {
    return <p style={{ fontSize: "0.875rem", color: "#666" }}>Waiting for the first step…</p>;
  }
  return (
    <ol aria-label="Trace" style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {steps.map((event, i) => (
        <li
          key={i}
          style={{
            display: "flex",
            gap: "0.75rem",
            alignItems: "baseline",
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "0.75rem",
            marginBottom: "0.5rem",
            fontSize: "0.875rem",
          }}
        >
          <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#999" }}>
            {i + 1}
          </span>
          <div>
            <div style={{ fontWeight: 600 }}>{NODE_LABELS[event.node] ?? event.node}</div>
            <div style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#999" }}>
              {event.node}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
