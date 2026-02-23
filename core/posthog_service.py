"""
PostHog Analytics Service for Backend
Handles server-side event tracking and analytics
"""

import os
from posthog import Posthog
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# PostHog Configuration
POSTHOG_KEY = os.getenv("POSTHOG_KEY", "phc_XWS39nnDqDtQQoE3h2CacRVsLG1CVjcHnJXbBjdTV6Z")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

# Initialize PostHog client
posthog_client: Optional[Posthog] = None


def init_posthog():
    """Initialize the PostHog client"""
    global posthog_client

    if posthog_client is not None:
        return posthog_client

    try:
        posthog_client = Posthog(
            project_api_key=POSTHOG_KEY,
            host=POSTHOG_HOST
        )
        logger.info("✅ PostHog initialized successfully")
        return posthog_client
    except Exception as e:
        logger.error(f"Failed to initialize PostHog: {e}")
        return None


def track_event(
    event_name: str,
    distinct_id: str,
    properties: Optional[Dict[str, Any]] = None,
):
    """
    Track a custom event

    Args:
        event_name: Name of the event to track
        distinct_id: Unique identifier for the user (user_id or email)
        properties: Additional event properties
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, skipping event tracking")
        return

    try:
        posthog_client.capture(
            distinct_id=str(distinct_id),
            event=event_name,
            properties=properties or {}
        )
        logger.debug(f"Tracked event: {event_name} for user: {distinct_id}")
    except Exception as e:
        logger.error(f"Failed to track event {event_name}: {e}")


def identify_user(
    user_id: str,
    properties: Optional[Dict[str, Any]] = None
):
    """
    Identify a user and set their properties

    Args:
        user_id: Unique identifier for the user
        properties: User properties to set
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, skipping user identification")
        return

    try:
        posthog_client.identify(
            distinct_id=str(user_id),
            properties=properties or {}
        )
        logger.debug(f"Identified user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to identify user {user_id}: {e}")


def set_user_properties(
    user_id: str,
    properties: Dict[str, Any]
):
    """
    Set or update user properties

    Args:
        user_id: Unique identifier for the user
        properties: Properties to set
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, skipping set user properties")
        return

    try:
        posthog_client.set(
            distinct_id=str(user_id),
            properties=properties
        )
        logger.debug(f"Set properties for user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to set properties for user {user_id}: {e}")


def reset_user(user_id: str):
    """
    Reset user (usually on logout)

    Args:
        user_id: Unique identifier for the user
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, skipping user reset")
        return

    try:
        posthog_client.alias(
            previous_id=str(user_id),
            distinct_id="anonymous"
        )
        logger.debug(f"Reset user: {user_id}")
    except Exception as e:
        logger.error(f"Failed to reset user {user_id}: {e}")


def is_feature_enabled(
    feature_flag: str,
    user_id: str
) -> bool:
    """
    Check if a feature flag is enabled for a user

    Args:
        feature_flag: Name of the feature flag
        user_id: Unique identifier for the user

    Returns:
        bool: True if feature is enabled, False otherwise
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, returning False for feature flag")
        return False

    try:
        return posthog_client.feature_enabled(
            key=feature_flag,
            distinct_id=str(user_id)
        )
    except Exception as e:
        logger.error(f"Failed to check feature flag {feature_flag}: {e}")
        return False


def capture_exception(
    error: Exception,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Capture an exception and send it to PostHog

    Args:
        error: The exception to capture
        user_id: Optional user ID associated with the error
        context: Optional additional context about the error
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, logging error locally")
        logger.error(f"Exception: {error}", exc_info=True)
        return

    try:
        error_data = {
            "$exception_type": type(error).__name__,
            "$exception_message": str(error),
            "$exception_stack_trace_raw": "".join(
                __import__("traceback").format_exception(type(error), error, error.__traceback__)
            ),
            **(context or {})
        }

        # Use user_id if provided, otherwise use a generic identifier
        distinct_id = user_id or "system"

        posthog_client.capture(
            distinct_id=str(distinct_id),
            event="$exception",
            properties=error_data
        )

        logger.debug(f"Captured exception: {type(error).__name__} for user: {distinct_id}")
    except Exception as e:
        logger.error(f"Failed to capture exception: {e}")


def capture_api_error(
    endpoint: str,
    method: str,
    status_code: int,
    error_message: str,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Capture an API error

    Args:
        endpoint: The API endpoint that failed
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code
        error_message: Error message
        user_id: Optional user ID
        context: Optional additional context
    """
    if posthog_client is None:
        logger.warning("PostHog not initialized, skipping API error tracking")
        return

    try:
        error_data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "error_message": error_message,
            "error_type": "api_error",
            **(context or {})
        }

        distinct_id = user_id or "system"

        track_event(
            event_name="api_error",
            distinct_id=distinct_id,
            properties=error_data
        )

        logger.debug(f"Captured API error: {method} {endpoint} - {status_code}")
    except Exception as e:
        logger.error(f"Failed to capture API error: {e}")


def shutdown_posthog():
    """Shutdown PostHog client and flush remaining events"""
    global posthog_client

    if posthog_client is not None:
        try:
            posthog_client.flush()
            posthog_client.shutdown()
            logger.info("PostHog client shut down successfully")
        except Exception as e:
            logger.error(f"Failed to shutdown PostHog: {e}")
        finally:
            posthog_client = None
