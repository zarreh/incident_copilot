"use client";

import { useEffect, useRef, useState } from "react";
import {
  createInvestigation,
  getInvestigation,
  streamInvestigationEvents,
} from "@/lib/api";
import type { InvestigationResponse, TraceEvent } from "@/lib/types";
import { TraceTimeline } from "./TraceTimeline";
import { ReportPanel } from "./ReportPanel";

type Phase = "loading" | "streaming" | "success" | "empty" | "error";

export function RunConsole({ question }: { question: string }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const cleanupRef = useRef<() => void>(() => {});

  useEffect(() => {
    let cancelled = false;

    async function finish(id: string) {
      try {
        const result = await getInvestigation(id);
        if (cancelled) return;
        setInvestigation(result);
        if (result.status === "failed") {
          setPhase("error");
          setErrorMessage(result.error ?? "The investigation failed.");
        } else if (!result.report) {
          setPhase("empty");
        } else {
          setPhase("success");
        }
      } catch {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Could not fetch the finished report.");
        }
      }
    }

    async function start() {
      setPhase("loading");
      setEvents([]);
      setInvestigation(null);
      setErrorMessage(null);
      try {
        const created = await createInvestigation(question);
        if (cancelled) return;
        setPhase("streaming");
        cleanupRef.current = streamInvestigationEvents(created.id, {
          onEvent: (event) => {
            if (cancelled) return;
            setEvents((prev) => [...prev, event]);
          },
          onEnd: () => {
            if (cancelled) return;
            void finish(created.id);
          },
          onError: () => {
            if (cancelled) return;
            setPhase("error");
            setErrorMessage("Lost connection to the investigation stream.");
          },
        });
      } catch {
        if (!cancelled) {
          setPhase("error");
          setErrorMessage("Could not start the investigation.");
        }
      }
    }

    void start();
    return () => {
      cancelled = true;
      cleanupRef.current();
    };
  }, [question]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <p
        style={{
          background: "#f5f5f5",
          borderRadius: "4px",
          padding: "0.5rem",
          fontSize: "0.8rem",
          color: "#555",
        }}
      >
        You asked: <strong>{question}</strong>
      </p>

      {phase === "loading" && (
        <p role="status" style={{ fontSize: "0.875rem", color: "#666" }}>
          Starting the investigation…
        </p>
      )}

      {phase === "error" && (
        <p
          role="alert"
          style={{
            background: "#fde2e1",
            color: "#7a1f1f",
            borderRadius: "4px",
            padding: "0.75rem",
            fontSize: "0.875rem",
          }}
        >
          {errorMessage}
        </p>
      )}

      {phase === "empty" && (
        <p
          role="status"
          style={{
            background: "#f5f5f5",
            color: "#555",
            borderRadius: "4px",
            padding: "0.75rem",
            fontSize: "0.875rem",
          }}
        >
          The investigation finished but produced no report.
        </p>
      )}

      {(phase === "streaming" || phase === "success" || phase === "empty") && (
        <TraceTimeline events={events} />
      )}

      {phase === "success" && investigation?.report && (
        <ReportPanel report={investigation.report} />
      )}

      {investigation && (phase === "success" || phase === "empty") && (
        <p style={{ fontSize: "0.75rem", color: "#999" }}>
          Total cost: ${investigation.total_cost_usd.toFixed(4)}
        </p>
      )}
    </div>
  );
}
