"""Re-export the shared ASGI middleware from `zarreh_agentkit`."""

from zarreh_agentkit.api.middleware import MaxBodySizeMiddleware

__all__ = ["MaxBodySizeMiddleware"]
