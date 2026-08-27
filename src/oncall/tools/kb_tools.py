"""LangChain tool wrapping the curated vendor/known-issue KB."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from oncall.retrieval.vendor_kb import VendorKB


class LookupKnownIssueArgs(BaseModel):
    vendor: str | None = Field(default=None, description="e.g. postgresql, redis, rabbitmq")
    symptom: str | None = Field(default=None, description="A symptom keyword or phrase to match")


def build_lookup_known_issue_tool(vendor_kb: VendorKB) -> StructuredTool:
    def _lookup(vendor: str | None = None, symptom: str | None = None) -> list[dict[str, object]]:
        issues = vendor_kb.find(vendor=vendor, symptom=symptom)
        return [
            {
                "id": i.id,
                "vendor": i.vendor,
                "symptoms": list(i.symptoms),
                "cause": i.cause,
                "mitigation": i.mitigation,
            }
            for i in issues
        ]

    return StructuredTool.from_function(
        func=_lookup,
        name="lookup_known_issue",
        description=(
            "Search the curated vendor/known-issue knowledge base by vendor and/or symptom keyword."
        ),
        args_schema=LookupKnownIssueArgs,
    )
