import type {
  CreateInvestigationResponse,
  InvestigationResponse,
  TraceEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

export async function createInvestigation(question: string): Promise<CreateInvestigationResponse> {
  const response = await fetch(`${API_BASE}/investigations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new ApiError(`Failed to start investigation (${response.status})`, response.status);
  }
  return response.json() as Promise<CreateInvestigationResponse>;
}

export async function getInvestigation(id: string): Promise<InvestigationResponse> {
  const response = await fetch(`${API_BASE}/investigations/${id}`);
  if (!response.ok) {
    throw new ApiError(`Failed to fetch investigation (${response.status})`, response.status);
  }
  return response.json() as Promise<InvestigationResponse>;
}

export type TraceEventHandlers = {
  onEvent: (event: TraceEvent) => void;
  onEnd: () => void;
  onError: () => void;
};

/** Subscribes to GET /investigations/{id}/events (SSE). Returns a cleanup
 * function that closes the connection — call it on unmount. */
export function streamInvestigationEvents(id: string, handlers: TraceEventHandlers): () => void {
  const source = new EventSource(`${API_BASE}/investigations/${id}/events`);
  source.onmessage = (message) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(message.data as string);
    } catch {
      handlers.onError();
      return;
    }
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("node" in parsed) ||
      typeof (parsed as { node: unknown }).node !== "string"
    ) {
      handlers.onError();
      return;
    }
    const event = parsed as TraceEvent;
    handlers.onEvent(event);
    if (event.node === "__end__") {
      source.close();
      handlers.onEnd();
    }
  };
  source.onerror = () => {
    source.close();
    handlers.onError();
  };
  return () => source.close();
}
