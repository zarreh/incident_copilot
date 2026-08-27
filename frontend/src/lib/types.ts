// Aliases over the OpenAPI-generated schema (see `npm run gen:types`, backed
// by `make frontend-types`). Regenerate `api-types.ts` whenever
// src/oncall/api/schemas.py or src/oncall/schemas/models.py change.
import type { components } from "./api-types";

export type Evidence = components["schemas"]["Evidence"];
export type IncidentReport = components["schemas"]["IncidentReport"];
export type CreateInvestigationResponse = components["schemas"]["CreateInvestigationResponse"];
export type CostSummaryEntry = components["schemas"]["CostSummaryEntry"];
export type InvestigationResponse = components["schemas"]["InvestigationResponse"];

/** One node's SSE event (oncall.api.streaming) — not part of the OpenAPI schema. */
export type TraceEvent = {
  node: string;
  output: unknown;
};
