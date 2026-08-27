"""LangChain tool wrapping read-only log search for the investigation graph."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from oncall.retrieval.log_store import LogStore


class SearchLogsArgs(BaseModel):
    service: str | None = Field(default=None, description="Filter by service name")
    level: str | None = Field(default=None, description="Filter by log level, e.g. ERROR")
    trace_id: str | None = Field(default=None, description="Filter by a specific trace id")
    since: str | None = Field(default=None, description="ISO timestamp lower bound")
    until: str | None = Field(default=None, description="ISO timestamp upper bound")
    limit: int = Field(default=50, ge=1, le=200, description="Max rows to return")


def build_search_logs_tool(log_store: LogStore) -> StructuredTool:
    """A tool over `log_store.query`; only the append-only logs table is
    reachable — never the incidents/fixtures ground-truth tables."""

    def _search(
        service: str | None = None,
        level: str | None = None,
        trace_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        rows = log_store.query(
            service=service,
            level=level,
            trace_id=trace_id,
            since=since,
            until=until,
            limit=limit,
        )
        return [
            {
                "timestamp": r.timestamp,
                "service": r.service,
                "level": r.level,
                "message": r.message,
                "trace_id": r.trace_id,
                "metadata": r.metadata,
            }
            for r in rows
        ]

    return StructuredTool.from_function(
        func=_search,
        name="search_logs",
        description=(
            "Search the incident log store. Filter by service, level, trace_id, "
            "and/or a time range. Returns up to `limit` matching log lines, "
            "newest first."
        ),
        args_schema=SearchLogsArgs,
    )
