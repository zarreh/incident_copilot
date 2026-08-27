from functools import lru_cache
from typing import Literal

from pydantic_settings import SettingsConfigDict
from zarreh_agentkit.settings import AgentSettings

WebSearchMode = Literal["off", "local", "live"]


class Settings(AgentSettings):
    """Application configuration, sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ONCALL_", extra="ignore")

    langsmith_project: str = "incident-investigation-copilot"

    # Data paths
    log_db_path: str = "data/logs.db"
    vendor_kb_path: str = "data/vendor_kb.json"
    run_store_path: str = "data/runs.db"
    checkpoint_db_path: str = "data/checkpoints.db"

    # Models
    fast_model: str = "gpt-4o-mini"
    reasoning_model: str = "gpt-4o"

    # Web search mode: off / local (curated vendor KB) / live (DuckDuckGo)
    web_search: WebSearchMode = "local"

    # Investigation budget
    max_tool_calls: int = 15
    max_run_seconds: float = 120.0

    # Sandbox
    sandbox_timeout_seconds: float = 30.0
    sandbox_memory_limit_mb: int = 256
    sandbox_cpu_period_us: int = 100_000
    sandbox_cpu_quota_us: int = 50_000

    max_request_body_bytes: int = 16_384


@lru_cache
def get_settings() -> Settings:
    return Settings()
