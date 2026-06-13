import os
import sys
import time
import logging
from typing import Optional, Literal
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from vrski.mcp.http_client import VrskiHttpClient

# Configure logging to stderr so it doesn't corrupt stdio channel
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("vrski.mcp.server")

try:
    import structlog as _structlog
    _tool_log = _structlog.get_logger("vrski.tool_calls")
except ImportError:
    _tool_log = None


def _log_tool_call(tool: str, params: dict, result: dict, duration_ms: float, session_id: str = "") -> None:
    entry = {
        "tool": tool,
        "session_id": session_id,
        "params": params,
        "result": {k: v for k, v in result.items() if k != "screenshot_base64"},
        "duration_ms": round(duration_ms, 1),
    }
    if _tool_log:
        _tool_log.info("tool_call", **entry)
    else:
        logger.info(f"tool_call {entry}")

# Initialize HTTP client pointing to FastAPI server
client = VrskiHttpClient()


@asynccontextmanager
async def mcp_lifespan(server: FastMCP):
    """Gracefully handles FastMCP lifespan events (startup & shutdown)."""
    try:
        yield
    finally:
        logger.info("FastMCP server shutting down, cleaning up client connections...")
        await client.close()


# Initialize FastMCP server with lifespan
mcp = FastMCP("vrski", lifespan=mcp_lifespan)


@mcp.tool()
async def vrski_start_session(session_id: str) -> dict:
    """Starts a new automation session or connects to an existing one.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post("/session/start", json={"session_id": session_id})


@mcp.tool()
async def vrski_end_session(session_id: str) -> dict:
    """Ends the specified automation session and cleans up resources.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post(f"/session/{session_id}/end")


@mcp.tool()
async def vrski_get_session_status(session_id: str) -> dict:
    """Retrieves the status (ready, busy, error) and metadata of a session.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.get(f"/session/{session_id}/status")


@mcp.tool()
async def vrski_get_screen(session_id: str, include_screenshot: bool = False, salient: bool = True) -> dict:
    """Gets the current screen state as a structured list of visible UI elements.

    By default returns only agent-relevant elements (text-bearing or interactive),
    dropping empty layout containers, the system status bar, and soft-keyboard keys.
    The response includes element_count and raw_element_count so you can see how much
    was filtered. Set salient=False to get the full raw accessibility tree.

    Args:
        session_id: The unique identifier for the automation session.
        include_screenshot: Whether to include the base64-encoded visual frame screenshot in the response.
        salient: When True (default), filter out non-interactive chrome/noise. Set False for the raw tree.
    """
    t0 = time.time()
    result = await client.get(f"/session/{session_id}/screen", params={"include_screenshot": include_screenshot, "salient": salient})
    _log_tool_call("vrski_get_screen", {"include_screenshot": include_screenshot, "salient": salient}, result, (time.time() - t0) * 1000, session_id)
    return result


@mcp.tool()
async def vrski_wait_for_element(
    session_id: str, 
    text: Optional[str] = None, 
    element_id: Optional[str] = None, 
    timeout: int = 15
) -> dict:
    """Blocks and polls the screen until an element matches the specified text or resource ID.
    
    Args:
        session_id: The unique identifier for the automation session.
        text: The text string of the element to wait for (optional).
        element_id: The Android resource ID of the element to wait for (optional).
        timeout: Maximum duration to wait in seconds (default is 15s).
    """
    return await client.post(f"/session/{session_id}/wait", json={
        "text": text,
        "element_id": element_id,
        "timeout": timeout
    })


@mcp.tool()
async def vrski_tap(
    session_id: str,
    text: Optional[str] = None,
    element_id: Optional[str] = None,
    content_desc: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None
) -> dict:
    """Taps a UI element on the screen.
    
    Prefer tapping by semantic 'text' or 'element_id'. Use raw 'x' and 'y' coordinates only as a last resort.
    
    Args:
        session_id: The unique identifier for the automation session.
        text: The text content of the element to tap (optional).
        element_id: The resource ID of the element to tap (optional).
        content_desc: The content description of the element to tap (optional).
        x: The absolute X-coordinate to tap (optional).
        y: The absolute Y-coordinate to tap (optional).
    """
    payload = {"type": "tap"}
    if text is not None: payload["text"] = text
    if element_id is not None: payload["element_id"] = element_id
    if content_desc is not None: payload["content_desc"] = content_desc
    if x is not None: payload["x"] = x
    if y is not None: payload["y"] = y
    t0 = time.time()
    result = await client.post(f"/session/{session_id}/action", json=payload)
    _log_tool_call("vrski_tap", {k: v for k, v in payload.items() if k != "type"}, result, (time.time() - t0) * 1000, session_id)
    return result


@mcp.tool()
async def vrski_type(session_id: str, text: str, clear_first: bool = True) -> dict:
    """Types text into the currently focused editable input field.
    
    Args:
        session_id: The unique identifier for the automation session.
        text: The text characters to type.
        clear_first: Whether to clear the field's existing text before typing (default is True).
    """
    return await client.post(f"/session/{session_id}/action", json={
        "type": "type",
        "text": text,
        "clear_first": clear_first
    })


@mcp.tool()
async def vrski_swipe(
    session_id: str,
    direction: Literal["up", "down", "left", "right"],
    distance: int = 500,
    speed: int = 300
) -> dict:
    """Performs a swipe gesture on the screen in the specified direction.
    
    Args:
        session_id: The unique identifier for the automation session.
        direction: The direction of the swipe gesture ("up", "down", "left", or "right").
        distance: The distance of the swipe gesture in pixels (default is 500).
        speed: The speed of the swipe swipe gesture (default is 300).
    """
    return await client.post(f"/session/{session_id}/action", json={
        "type": "swipe",
        "direction": direction,
        "distance": distance,
        "speed": speed
    })


@mcp.tool()
async def vrski_scroll_to(session_id: str, text: str) -> dict:
    """Scrolls the screen in a loop until an element matching the given text becomes visible.
    
    Args:
        session_id: The unique identifier for the automation session.
        text: The text string of the element to scroll to.
    """
    return await client.post(f"/session/{session_id}/action", json={
        "type": "scroll_to",
        "text": text
    })


@mcp.tool()
async def vrski_back(session_id: str) -> dict:
    """Presses the hardware Back button on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post(f"/session/{session_id}/action", json={"type": "back"})


@mcp.tool()
async def vrski_home(session_id: str) -> dict:
    """Presses the hardware Home button on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post(f"/session/{session_id}/action", json={"type": "home"})


@mcp.tool()
async def vrski_recent_apps(session_id: str) -> dict:
    """Opens the hardware Recent Apps screen on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post(f"/session/{session_id}/action", json={"type": "recent_apps"})


@mcp.tool()
async def vrski_install_app(session_id: str, package_name: str) -> dict:
    """Downloads and installs the specified application package from Google Play Store.
    
    Args:
        session_id: The unique identifier for the automation session.
        package_name: The Android package name (e.g. "com.whatsapp").
    """
    return await client.post(f"/session/{session_id}/install", json={"package_name": package_name})


@mcp.tool()
async def vrski_uninstall_app(session_id: str, package_name: str) -> dict:
    """Uninstalls the specified application package from the device.
    
    Args:
        session_id: The unique identifier for the automation session.
        package_name: The Android package name (e.g. "com.whatsapp").
    """
    return await client.post(f"/session/{session_id}/uninstall", json={"package_name": package_name})


@mcp.tool()
async def vrski_launch_app(session_id: str, package_name: str) -> dict:
    """Launches the specified application package on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
        package_name: The Android package name (e.g. "com.whatsapp").
    """
    return await client.post(f"/session/{session_id}/launch", json={"package_name": package_name})


@mcp.tool()
async def vrski_close_app(session_id: str, package_name: str) -> dict:
    """Closes or force-stops the specified application package on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
        package_name: The Android package name (e.g. "com.whatsapp").
    """
    return await client.post(f"/session/{session_id}/close", json={"package_name": package_name})


@mcp.tool()
async def vrski_is_installed(session_id: str, package_name: str) -> dict:
    """Checks whether the specified application package is installed on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
        package_name: The Android package name (e.g. "com.whatsapp").
    """
    return await client.get(f"/session/{session_id}/apps/{package_name}")


@mcp.tool()
async def vrski_list_installed(session_id: str) -> dict:
    """Lists all application packages installed on the device.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.get(f"/session/{session_id}/apps")


@mcp.tool()
async def vrski_signin_playstore(
    session_id: str,
    gmail: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """Authenticates the device to the Google Play Store.

    If gmail/password are omitted, credentials stored via vrski_setup() are used
    automatically. Only pass credentials explicitly if overriding saved ones.

    Args:
        session_id: The unique identifier for the automation session.
        gmail: Google Account email. Omit to use saved credentials from vrski_setup().
        password: Google Account password. Omit to use saved credentials from vrski_setup().
    """
    return await client.post(f"/session/{session_id}/auth/playstore", json={
        "gmail": gmail,
        "password": password,
    })


@mcp.tool()
async def vrski_get_playstore_account(session_id: str) -> dict:
    """Retrieves the active Google Account signed in on the Google Play Store.
    
    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.get(f"/session/{session_id}/auth/playstore")


@mcp.tool()
async def vrski_dismiss_popups(session_id: str) -> dict:
    """Dismisses any blocking Android popups currently on screen.

    Call this before any action if you suspect a dialog is blocking the UI
    (permission request, Play Store update prompt, 'app not responding', etc.).

    Args:
        session_id: The unique identifier for the automation session.
    """
    return await client.post(f"/session/{session_id}/dismiss_popups")


@mcp.tool()
async def vrski_setup(session_id: str, email: str, password: str) -> dict:
    """First-run onboarding: saves the owner's Google credentials and signs into Play Store.

    Call this ONCE when the owner provides their Google account details.
    Credentials are stored in .env and reused automatically on every future session —
    the owner never needs to provide them again.

    Typical Hermes / agent harness flow:
        1. status = vrski_check_setup(session_id)
        2. if not status["ready"]: ask owner for email + password
        3. vrski_setup(session_id, email=..., password=...)
        4. All future sessions: vrski_check_setup returns ready=true, no owner prompt needed.

    Args:
        session_id: The automation session ID (must be started first).
        email: Owner's Google account email address.
        password: Owner's Google account password.
    """
    return await client.post("/setup", json={
        "session_id": session_id,
        "email": email,
        "password": password,
    })


@mcp.tool()
async def vrski_check_setup(session_id: str) -> dict:
    """Checks if the device is ready to use — credentials saved and Google account signed in.

    Returns:
        ready (bool): True if credentials are saved and device is authenticated.
        has_credentials (bool): True if email/password are stored in .env.
        saved_email (str | null): The stored Google email, if any.
        signed_in (bool): Whether the device currently has an active Google session.
        active_account (str | null): The signed-in Google account on the device.
        next_step (str | null): Human-readable instruction if not ready.

    Call at the start of every session. If ready=false:
      - has_credentials=false → ask owner for email/password, call vrski_setup()
      - has_credentials=true  → call vrski_signin_playstore() to restore the session

    Args:
        session_id: The automation session ID.
    """
    return await client.get("/setup/status", params={"session_id": session_id})


def run():
    """Starts the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    run()
