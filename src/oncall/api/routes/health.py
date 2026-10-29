from zarreh_agentkit.api.health import build_health_router

from oncall.api.rate_limit import DEFAULT_RATE_LIMIT, limiter

router = build_health_router(limiter, DEFAULT_RATE_LIMIT)
