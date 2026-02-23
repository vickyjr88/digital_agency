"""
Error Tracking Middleware for FastAPI
Captures and reports all unhandled exceptions to PostHog
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Callable
from core.posthog_service import capture_exception, capture_api_error

logger = logging.getLogger(__name__)


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch and track all unhandled exceptions
    """

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except Exception as error:
            # Log the error
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                exc_info=True
            )

            # Extract user ID from request if available
            user_id = None
            try:
                # Try to get user from request state (set by auth middleware)
                if hasattr(request.state, 'user'):
                    user_id = str(request.state.user.id)
            except Exception:
                pass

            # Capture exception to PostHog
            try:
                capture_exception(
                    error=error,
                    user_id=user_id,
                    context={
                        "endpoint": str(request.url.path),
                        "method": request.method,
                        "query_params": dict(request.query_params),
                        "path_params": dict(request.path_params),
                        "client_host": request.client.host if request.client else None,
                        "user_agent": request.headers.get("user-agent"),
                    }
                )
            except Exception as capture_error:
                logger.error(f"Failed to capture exception: {capture_error}")

            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "message": str(error) if logger.level == logging.DEBUG else "An unexpected error occurred",
                }
            )


async def http_exception_handler(request: Request, exc):
    """
    Custom HTTP exception handler to track API errors
    """
    from fastapi.exceptions import HTTPException

    # Extract user ID from request if available
    user_id = None
    try:
        if hasattr(request.state, 'user'):
            user_id = str(request.state.user.id)
    except Exception:
        pass

    # Track error in PostHog
    try:
        capture_api_error(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=exc.status_code,
            error_message=str(exc.detail),
            user_id=user_id,
            context={
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )
    except Exception as capture_error:
        logger.error(f"Failed to capture API error: {capture_error}")

    # Return the error response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def validation_exception_handler(request: Request, exc):
    """
    Handler for validation errors
    """
    from fastapi.exceptions import RequestValidationError

    # Track validation error
    user_id = None
    try:
        if hasattr(request.state, 'user'):
            user_id = str(request.state.user.id)
    except Exception:
        pass

    try:
        capture_api_error(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=422,
            error_message="Validation error",
            user_id=user_id,
            context={
                "validation_errors": exc.errors(),
                "body": str(exc.body) if hasattr(exc, 'body') else None,
            }
        )
    except Exception as capture_error:
        logger.error(f"Failed to capture validation error: {capture_error}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )
