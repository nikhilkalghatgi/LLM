"""Starlette middleware: request timing and upload size limiting."""

import time
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from serve.schemas import ErrorResponse


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Times each request, sets an X-Process-Time header, and logs a line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        process_time = time.time() - start

        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{timestamp}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({process_time:.2f}s)",
            flush=True,
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Content-Length exceeds the configured limit."""

    def __init__(self, app, max_upload_size_mb: int = 50) -> None:
        super().__init__(app)
        self.max_bytes = max_upload_size_mb * 1024 * 1024
        self.max_upload_size_mb = max_upload_size_mb

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    payload = ErrorResponse(
                        error="Payload too large",
                        detail=(
                            f"Request body exceeds the "
                            f"{self.max_upload_size_mb} MB limit."
                        ),
                    )
                    return JSONResponse(status_code=413, content=payload.model_dump())
            except ValueError:
                # Malformed Content-Length - let it fall through to the app.
                pass

        return await call_next(request)

