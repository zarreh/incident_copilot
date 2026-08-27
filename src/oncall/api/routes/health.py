from fastapi import APIRouter, Request

from oncall.api.rate_limit import DEFAULT_RATE_LIMIT, limiter

router = APIRouter(tags=["health"])


@router.get("/healthz")
@limiter.limit(DEFAULT_RATE_LIMIT)
def healthz(request: Request) -> dict[str, str]:  # noqa: ARG001
    return {"status": "ok"}
