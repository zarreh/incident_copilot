"""Single shared `Limiter` instance for the oncall API."""

from zarreh_agentkit.api.rate_limit import build_limiter, default_rate_limit

from oncall.settings import get_settings

limiter = build_limiter()
DEFAULT_RATE_LIMIT = default_rate_limit(get_settings())
