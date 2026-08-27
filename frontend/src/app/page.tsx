"use client";

import { useState } from "react";
import { RunConsole } from "@/components/RunConsole";

// First paint first: a visitor lands and watches a full investigation stream
// node-by-node against a preloaded example, before typing anything. The
// scenarios below map onto the five seeded incidents plus the adversarial
// fixture in data/generate_logs.py, so the retrieved evidence actually exists.
const SCENARIOS = {
  paymentTimeout: {
    label: "Payment timeouts",
    question: "Why are payment-service requests timing out?",
  },
  authRegression: {
    label: "Auth-service errors",
    question: "Why is auth-service rejecting logins after the latest deploy?",
  },
  dbPool: {
    label: "Database pool exhaustion",
    question: "Why is the database connection pool exhausted?",
  },
  cacheStampede: {
    label: "Catalog cache stampede",
    question: "Why is the catalog service slow — is this a cache problem?",
  },
  workerCrash: {
    label: "Notification worker crashes",
    question: "Why does the notification queue worker keep crash-looping?",
  },
  adversarial: {
    label: "Traffic spike (is it an attack?)",
    question: "We saw a big traffic spike overnight — were we attacked?",
  },
} as const;

type ScenarioKey = keyof typeof SCENARIOS;

export default function Home() {
  const [scenario, setScenario] = useState<ScenarioKey>("paymentTimeout");
  const [customQuestion, setCustomQuestion] = useState("");
  const [activeQuestion, setActiveQuestion] = useState<string>(
    SCENARIOS.paymentTimeout.question
  );

  function selectScenario(key: ScenarioKey) {
    setScenario(key);
    setActiveQuestion(SCENARIOS[key].question);
  }

  function submitCustomQuestion(e: React.FormEvent) {
    e.preventDefault();
    if (!customQuestion.trim()) return;
    setActiveQuestion(customQuestion.trim());
  }

  return (
    <main style={{ maxWidth: "48rem", margin: "0 auto", padding: "2rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Incident Investigation Copilot</h1>
      <p style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "#555" }}>
        An on-call assistant that searches logs, checks a curated known-issue
        knowledge base, and runs sandboxed diagnostics before drafting an
        incident report — streamed step by step so you can watch the
        evidence-citation guardrail work. Runs entirely on fully synthetic data.
      </p>

      <div
        role="group"
        aria-label="Example incidents"
        style={{ marginTop: "1.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem" }}
      >
        {(Object.keys(SCENARIOS) as ScenarioKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => selectScenario(key)}
            aria-pressed={scenario === key && activeQuestion === SCENARIOS[key].question}
            style={{
              borderRadius: "4px",
              padding: "0.4rem 0.75rem",
              fontSize: "0.85rem",
              cursor: "pointer",
              border:
                scenario === key && activeQuestion === SCENARIOS[key].question
                  ? "1px solid #111"
                  : "1px solid #ccc",
              background:
                scenario === key && activeQuestion === SCENARIOS[key].question
                  ? "#111"
                  : "#fff",
              color:
                scenario === key && activeQuestion === SCENARIOS[key].question
                  ? "#fff"
                  : "#333",
            }}
          >
            {SCENARIOS[key].label}
          </button>
        ))}
      </div>

      <form
        onSubmit={submitCustomQuestion}
        style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}
      >
        <input
          type="text"
          value={customQuestion}
          onChange={(e) => setCustomQuestion(e.target.value)}
          placeholder="Or ask your own question…"
          aria-label="Custom question"
          style={{
            flex: 1,
            padding: "0.5rem",
            border: "1px solid #ccc",
            borderRadius: "4px",
            fontSize: "0.875rem",
          }}
        />
        <button
          type="submit"
          style={{
            padding: "0.5rem 1rem",
            borderRadius: "4px",
            border: "1px solid #111",
            background: "#111",
            color: "#fff",
            fontSize: "0.875rem",
            cursor: "pointer",
          }}
        >
          Investigate
        </button>
      </form>

      <div style={{ marginTop: "1.5rem" }}>
        {/* Re-key on the active question so switching restarts the run from scratch. */}
        <RunConsole key={activeQuestion} question={activeQuestion} />
      </div>
    </main>
  );
}
