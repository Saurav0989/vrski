import pytest
import os
import httpx
from unittest.mock import AsyncMock, patch

# Ensure API runs in simulation mode
os.environ["VRSKI_SIMULATE"] = "true"

# Import mcp tools
from vrski.mcp.server import (
    mcp,
    vrski_start_session,
    vrski_end_session,
    vrski_get_session_status,
    vrski_get_screen,
    vrski_wait_for_element,
    vrski_tap,
    vrski_type,
    vrski_swipe,
    vrski_scroll_to,
    vrski_back,
    vrski_home,
    vrski_recent_apps,
    vrski_install_app,
    vrski_uninstall_app,
    vrski_launch_app,
    vrski_close_app,
    vrski_is_installed,
    vrski_list_installed,
    vrski_signin_playstore,
    vrski_get_playstore_account
)


@pytest.mark.asyncio
async def test_mcp_tools_registration():
    # Verify that all tools are registered in the FastMCP server
    tools = mcp._tool_manager.list_tools()
    assert len(tools) >= 20
    tool_names = [t.name for t in tools]
    assert "vrski_start_session" in tool_names
    assert "vrski_end_session" in tool_names
    assert "vrski_get_screen" in tool_names
    assert "vrski_tap" in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_execution():
    from vrski.mcp.server import client as mcp_client
    
    # Mock return values for FastAPI responses
    async def mock_get(path, params=None):
        if "status" in path:
            return {"success": True, "session_id": "test_s", "status": "ready", "current_app": "com.android.settings"}
        elif "screen" in path:
            return {"success": True, "elements": [{"id": "el1", "type": "Button", "text": "Click"}], "package": "com.android.settings", "activity": ".Settings"}
        elif "apps" in path:
            parts = path.rstrip("/").split("/")
            if len(parts) > 1 and parts[-2] == "apps":
                return {"success": True, "installed": True}
            return {"success": True, "packages": ["com.android.settings"]}
        elif "auth/playstore" in path:
            return {"success": True, "signed_in": True, "account": "vrski.agent@gmail.com"}
        return {"success": True}

    async def mock_post(path, json=None):
        if "start" in path:
            return {"success": True, "session_id": "test_s", "status": "ready", "emulator_serial": "emulator-5554"}
        elif "end" in path:
            return {"success": True, "status": "ended"}
        elif "action" in path:
            return {"success": True, "matched_element": "el1"}
        elif "install" in path:
            return {"success": True, "package_name": json.get("package_name"), "duration_seconds": 1.5}
        elif "uninstall" in path:
            return {"success": True}
        elif "wait" in path:
            return {"success": True, "found": True, "element": {"id": "el1"}}
        return {"success": True}

    # Patch client methods
    with patch.object(mcp_client, "get", side_effect=mock_get), \
         patch.object(mcp_client, "post", side_effect=mock_post):
         
        # 1. Start session
        res = await vrski_start_session(session_id="test_s")
        assert res["success"] is True
        assert res["session_id"] == "test_s"

        # 2. Get status
        res = await vrski_get_session_status(session_id="test_s")
        assert res["success"] is True
        assert res["status"] == "ready"

        # 3. Get screen
        res = await vrski_get_screen(session_id="test_s")
        assert res["success"] is True
        assert len(res["elements"]) == 1

        # 4. Wait for element
        res = await vrski_wait_for_element(session_id="test_s", text="Click")
        assert res["success"] is True
        assert res["found"] is True

        # 5. Tap
        res = await vrski_tap(session_id="test_s", text="Click")
        assert res["success"] is True
        assert res["matched_element"] == "el1"

        # 6. Type
        res = await vrski_type(session_id="test_s", text="Hello")
        assert res["success"] is True

        # 7. Swipe
        res = await vrski_swipe(session_id="test_s", direction="up")
        assert res["success"] is True

        # 8. Scroll
        res = await vrski_scroll_to(session_id="test_s", text="Target")
        assert res["success"] is True

        # 9. Keypresses
        assert (await vrski_back(session_id="test_s"))["success"] is True
        assert (await vrski_home(session_id="test_s"))["success"] is True
        assert (await vrski_recent_apps(session_id="test_s"))["success"] is True

        # 10. Playstore Auth
        res = await vrski_signin_playstore(session_id="test_s", gmail="a@b.com", password="123")
        assert res["success"] is True
        
        res = await vrski_get_playstore_account(session_id="test_s")
        assert res["success"] is True
        assert res["account"] == "vrski.agent@gmail.com"

        # 11. Apps
        res = await vrski_install_app(session_id="test_s", package_name="com.instagram.android")
        assert res["success"] is True
        
        res = await vrski_uninstall_app(session_id="test_s", package_name="com.instagram.android")
        assert res["success"] is True

        res = await vrski_is_installed(session_id="test_s", package_name="com.instagram.android")
        assert res["success"] is True
        assert res["installed"] is True

        res = await vrski_list_installed(session_id="test_s")
        assert res["success"] is True
        assert "com.android.settings" in res["packages"]

        # 12. App launch / close
        res = await vrski_launch_app(session_id="test_s", package_name="com.instagram.android")
        assert res["success"] is True
        
        res = await vrski_close_app(session_id="test_s", package_name="com.instagram.android")
        assert res["success"] is True

        # 13. End session
        res = await vrski_end_session(session_id="test_s")
        assert res["success"] is True
        assert res["status"] == "ended"


@pytest.mark.asyncio
async def test_mcp_client_connection_error():
    """Verify HTTP client handles connection exceptions gracefully."""
    from vrski.mcp.server import client as mcp_client
    
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Failed to connect to host")
    
    with patch.object(mcp_client, "get_client", return_value=mock_client):
        res = await vrski_get_session_status(session_id="test_s")
        assert res["success"] is False
        assert "Connection error" in res["error"]


@pytest.mark.asyncio
async def test_mcp_client_http_error_status():
    """Verify HTTP client handles non-200 status codes gracefully."""
    from vrski.mcp.server import client as mcp_client
    
    mock_client = AsyncMock()
    mock_response = httpx.Response(status_code=500, content=b"Internal Server Error")
    mock_client.post.return_value = mock_response
    
    with patch.object(mcp_client, "get_client", return_value=mock_client):
        res = await vrski_start_session(session_id="test_s")
        assert res["success"] is False
        assert "HTTP 500" in res["error"]
