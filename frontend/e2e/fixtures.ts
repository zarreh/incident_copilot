// Shared fixtures for the Playwright smoke tests. The backend is fully mocked
// at the network layer: no live LLM or Python process is needed, so a
// screenshot can never silently drift from what the smoke test proves the UI does.

export const REPORT_PAYLOAD = {
  title: "payment-service timeout cascade",
  severity: "high",
  root_cause:
    "payment-service requests are timing out waiting on a slow downstream call, " +
    "consistent with the upstream latency seen in the retrieved logs.",
  evidence: [
    {
      source: "log",
      reference: "trace-payment-9f21",
      detail: "payment-service request exceeded the configured timeout",
    },
  ],
  recommended_actions: ["add a circuit breaker around the downstream call"],
  confidence: 0.87,
  insufficient_evidence: false,
};

export const INSUFFICIENT_REPORT_PAYLOAD = {
  ...REPORT_PAYLOAD,
  root_cause:
    "traffic spike looks like an attack [unverifiable: no anomalous log or " +
    "known-issue evidence supports this severity claim]",
  evidence: [],
  confidence: 0.0,
  insufficient_evidence: true,
};

export const ANSWERED_INVESTIGATION = {
  id: "run-success",
  question: "Why are payment-service requests timing out?",
  status: "completed",
  created_at: "2026-08-25T00:00:00Z",
  updated_at: "2026-08-25T00:00:05Z",
  report: REPORT_PAYLOAD,
  error: null,
  total_cost_usd: 0.0021,
  costs: [
    {
      node: "summarize",
      model: "gpt-4o",
      prompt_tokens: 800,
      completion_tokens: 120,
      cost_usd: 0.0021,
    },
  ],
};

export const INSUFFICIENT_INVESTIGATION = {
  ...ANSWERED_INVESTIGATION,
  id: "run-insufficient",
  question: "We saw a big traffic spike overnight — were we attacked?",
  report: INSUFFICIENT_REPORT_PAYLOAD,
};

const ANSWERED_NODES = ["agent", "tools", "agent", "summarize", "verify"];

export function sseBody(nodes: string[], finalPayload: { status: string; report: unknown }): string {
  const lines = nodes.map((node) => `data: ${JSON.stringify({ node, output: {} })}\n\n`);
  lines.push(`data: ${JSON.stringify({ node: "__end__", output: finalPayload })}\n\n`);
  return lines.join("");
}

export const ANSWERED_SSE = sseBody(ANSWERED_NODES, {
  status: "completed",
  report: REPORT_PAYLOAD,
});

export const INSUFFICIENT_SSE = sseBody(ANSWERED_NODES, {
  status: "completed",
  report: INSUFFICIENT_REPORT_PAYLOAD,
});

export const EMPTY_SSE = sseBody(ANSWERED_NODES, { status: "completed", report: null });
