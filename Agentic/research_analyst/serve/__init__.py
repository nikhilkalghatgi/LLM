"""Serve module — FastAPI application, request/response schemas, and middleware.

The FastAPI app lives in ``serve.api`` (entrypoint ``serve.api:app``). It is not
imported here to keep ``serve.schemas`` / ``serve.middleware`` importable without
loading the full model stack.
"""

__all__ = ["app"]


def __getattr__(name):  # PEP 562 lazy attribute access
    if name == "app":
        from .api import app

        return app
    raise AttributeError(f"module 'serve' has no attribute '{name}'")

