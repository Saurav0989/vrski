"""
Retry utilities for Vrski UI actions.

The async `with_retry` wrapper retries any async callable that returns a dict
with a "success" key. Synchronous callers can use `with_retry_sync`.
"""
import asyncio
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("vrski.utils.retry")


async def with_retry(
    fn: Callable,
    attempts: int = 3,
    delay: float = 1.0,
    label: str = "",
) -> dict:
    """Retries an async callable with exponential backoff.

    The callable must return a dict. Retry is triggered when:
    - The dict has success=False (transient UI failure), OR
    - The callable raises an exception.

    Args:
        fn: Async callable that returns a result dict.
        attempts: Maximum number of attempts.
        delay: Base delay in seconds (doubles each attempt).
        label: Optional label for log messages.
    """
    last_result: Optional[dict] = None
    for i in range(attempts):
        try:
            result = await fn()
            if isinstance(result, dict) and result.get("success"):
                return result
            last_result = result
            if i < attempts - 1:
                wait = delay * (2 ** i)
                logger.warning(f"[{label or 'retry'}] Attempt {i+1} failed (success=False). Retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)
        except Exception as e:
            last_result = {"success": False, "error": str(e)}
            if i == attempts - 1:
                logger.error(f"[{label or 'retry'}] All {attempts} attempts failed. Last error: {e}")
                raise
            wait = delay * (2 ** i)
            logger.warning(f"[{label or 'retry'}] Attempt {i+1} raised: {e}. Retrying in {wait:.1f}s...")
            await asyncio.sleep(wait)
    return last_result or {"success": False, "error": f"All {attempts} attempts failed"}


def with_retry_sync(
    fn: Callable,
    attempts: int = 3,
    delay: float = 1.0,
    label: str = "",
) -> Any:
    """Synchronous version of with_retry using time.sleep."""
    import time
    last_result = None
    for i in range(attempts):
        try:
            result = fn()
            if isinstance(result, dict) and result.get("success"):
                return result
            last_result = result
            if i < attempts - 1:
                wait = delay * (2 ** i)
                logger.warning(f"[{label or 'retry'}] Attempt {i+1} failed. Retrying in {wait:.1f}s...")
                time.sleep(wait)
        except Exception as e:
            last_result = {"success": False, "error": str(e)}
            if i == attempts - 1:
                logger.error(f"[{label or 'retry'}] All {attempts} attempts failed. Last error: {e}")
                raise
            wait = delay * (2 ** i)
            logger.warning(f"[{label or 'retry'}] Attempt {i+1} raised: {e}. Retrying in {wait:.1f}s...")
            time.sleep(wait)
    return last_result or {"success": False, "error": f"All {attempts} attempts failed"}
