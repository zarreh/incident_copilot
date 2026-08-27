"""Builds the LangChain tools available to the investigation graph."""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.settings import Settings
from oncall.tools.kb_tools import build_lookup_known_issue_tool
from oncall.tools.log_tools import build_search_logs_tool
from oncall.tools.sandbox_tools import build_run_diagnostic_tool


def build_tools(
    log_store: LogStore, vendor_kb: VendorKB, settings: Settings
) -> list[StructuredTool]:
    return [
        build_search_logs_tool(log_store),
        build_lookup_known_issue_tool(vendor_kb),
        build_run_diagnostic_tool(settings),
    ]
