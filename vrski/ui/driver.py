import os
import re
import io
import base64
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, Tuple
from vrski.ui.element import Bounds, UIElement, is_editable_type

logger = logging.getLogger("vrski.ui.driver")

# Attempt importing uiautomator2
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False
    u2 = None

BOUNDS_PATTERN = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

def parse_bounds(bounds_str: str) -> Optional[Bounds]:
    """Parses a bounds string of format '[left,top][right,bottom]'."""
    if not bounds_str:
        return None
    try:
        match = BOUNDS_PATTERN.match(bounds_str)
        if match:
            left, top, right, bottom = map(int, match.groups())
            return Bounds(left=left, top=top, right=right, bottom=bottom)
    except Exception as e:
        logger.warning(f"Error parsing bounds string '{bounds_str}' with pattern: {e}")
        
    # Fallback to extract any 4 numbers if the pattern didn't match cleanly
    try:
        nums = [int(n) for n in re.findall(r"-?\d+", bounds_str)]
        if len(nums) == 4:
            logger.info(f"Fallback parsing succeeded for bounds '{bounds_str}' -> {nums}")
            return Bounds(left=nums[0], top=nums[1], right=nums[2], bottom=nums[3])
    except Exception as e:
        logger.warning(f"Fallback bounds parsing also failed for '{bounds_str}': {e}")
    return None

class DeviceDriver:
    def __init__(self, serial: Optional[str] = None, mock: Optional[bool] = None):
        self.serial = serial
        
        # Determine mock mode
        if mock is not None:
            self.mock = mock
        else:
            env_mock = os.environ.get("VRSKI_MOCK", "").lower() in ("1", "true", "yes")
            self.mock = env_mock or not U2_AVAILABLE
            
        self.d = None
        if not self.mock:
            try:
                logger.info(f"Connecting to uiautomator2 (serial: {self.serial or 'default'})")
                self.d = u2.connect(self.serial)
                # Quick check to ensure it works
                _ = self.d.info
            except Exception as e:
                logger.warning(f"Failed to connect to uiautomator2: {e}. Falling back to mock mode.")
                self.mock = True

        if self.mock:
            logger.info("DeviceDriver initialized in MOCK mode")
            self._mock_xml = self._get_default_mock_xml()
        else:
            logger.info("DeviceDriver connected successfully")

    def is_connected(self) -> bool:
        """Checks if the device connection is active and responding."""
        if self.mock:
            return True
        if not self.d:
            return False
        try:
            # Quick check to query system info
            _ = self.d.info
            return True
        except Exception:
            return False

    def reconnect(self) -> bool:
        """Attempts to reconnect to the device via uiautomator2."""
        if self.mock:
            return True
        logger.info(f"Attempting to reconnect to uiautomator2 (serial: {self.serial or 'default'})")
        try:
            if not U2_AVAILABLE:
                logger.warning("uiautomator2 package is not available for reconnection.")
                return False
            self.d = u2.connect(self.serial)
            _ = self.d.info
            logger.info("Successfully reconnected to uiautomator2.")
            return True
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
            return False

    def _ensure_connected(self) -> bool:
        """Ensures the connection is active, attempting reconnection if necessary."""
        if self.mock:
            return True
        if self.is_connected():
            return True
        logger.warning("Device connection check failed. Attempting auto-reconnection...")
        return self.reconnect()

    def _get_default_mock_xml(self) -> str:
        """Default mock XML hierarchy resembling Android Settings screen."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]" clickable="false" scrollable="false">
    <node index="0" text="Settings" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[32,80][300,150]" clickable="false" scrollable="false"/>
    <node index="1" text="Network &amp; internet" resource-id="com.android.settings:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[64,200][1000,280]" clickable="true" scrollable="false"/>
    <node index="2" text="Connected devices" resource-id="com.android.settings:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[64,300][1000,380]" clickable="true" scrollable="false"/>
    <node index="3" text="Bluetooth" resource-id="com.android.settings:id/bluetooth_option" class="android.widget.Button" package="com.android.settings" bounds="[64,400][1000,500]" clickable="true" scrollable="false"/>
    <node index="4" text="Search settings" resource-id="com.android.settings:id/search_action_bar" class="android.widget.EditText" package="com.android.settings" bounds="[64,550][1000,650]" clickable="true" scrollable="false"/>
  </node>
</hierarchy>
"""

    def set_mock_xml(self, xml_str: str) -> None:
        """Allows overriding the mock XML tree for tests."""
        if self.mock:
            self._mock_xml = xml_str

    def get_hierarchy_xml(self) -> str:
        """Retrieves the raw XML hierarchy dump from the device."""
        if self.mock:
            return self._mock_xml
        if not self._ensure_connected():
            logger.error("Reconnection failed. Cannot retrieve hierarchy.")
            raise RuntimeError("Device connection lost and reconnection failed.")
        try:
            return self.d.dump_hierarchy()
        except Exception as e:
            logger.error(f"Failed to get hierarchy XML: {e}")
            if self.reconnect():
                try:
                    return self.d.dump_hierarchy()
                except Exception as e2:
                    logger.error(f"Retry dump hierarchy failed: {e2}")
            raise

    def get_tree(self) -> List[UIElement]:
        """Parses the current screen XML hierarchy into UIElement dataclasses."""
        try:
            xml_str = self.get_hierarchy_xml()
        except Exception as e:
            logger.error(f"Failed to retrieve hierarchy XML for tree: {e}")
            return []
            
        elements = []
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                attrib = node.attrib
                bounds_str = attrib.get("bounds", "")
                bounds = parse_bounds(bounds_str)
                if not bounds:
                    continue
                
                element_id = attrib.get("resource-id", "")
                class_name = attrib.get("class", "")
                element_type = class_name.split(".")[-1] if class_name else "View"
                text = attrib.get("text", "")
                content_desc = attrib.get("content-desc", "")
                
                # Check interaction tags
                clickable = attrib.get("clickable", "false").lower() == "true"
                scrollable = attrib.get("scrollable", "false").lower() == "true"
                
                # Deduce editable status (text-input widget classes only)
                editable = is_editable_type(element_type)
                
                elements.append(UIElement(
                    element_id=element_id,
                    element_type=element_type,
                    text=text,
                    content_desc=content_desc,
                    clickable=clickable,
                    scrollable=scrollable,
                    editable=editable,
                    bounds=bounds
                ))
        except Exception as e:
            logger.error(f"Failed to parse hierarchy XML: {e}")
        return elements

    def click(self, x: int, y: int) -> bool:
        """Performs a raw tap at coordinates (x, y)."""
        if self.mock:
            logger.info(f"[Mock] Click at ({x}, {y})")
            return True
        if not self._ensure_connected():
            logger.error(f"Cannot click at ({x}, {y}): connection lost.")
            return False
        try:
            self.d.click(x, y)
            return True
        except Exception as e:
            logger.error(f"Failed to click at ({x}, {y}): {e}")
            if self.reconnect():
                try:
                    self.d.click(x, y)
                    return True
                except Exception as e2:
                    logger.error(f"Retry click failed: {e2}")
            return False

    def send_keys(self, text: str) -> bool:
        """Types text into the currently focused element."""
        if self.mock:
            logger.info(f"[Mock] Send keys: '{text}'")
            return True
        if not self._ensure_connected():
            logger.error(f"Cannot send keys '{text}': connection lost.")
            return False
        # Require a focused field. Typing into nothing must fail loudly rather than
        # silently no-op: `adb input text` returns success even with no focused
        # input, so an agent would believe it typed when nothing happened.
        focused_el = self.d(focused=True)
        if not focused_el.wait(timeout=3.0):
            logger.warning("send_keys: no focused input field on screen; refusing to type into nothing.")
            return False
        # A field has focus — set_text is most reliable; fall back to `adb input
        # text` only because we've confirmed a field is focused to receive the keys.
        try:
            focused_el.set_text(text)
            return True
        except Exception as e:
            logger.warning(f"set_text on focused element failed: {e}; trying adb input text")
        try:
            import subprocess
            escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
            cmd = ["adb"]
            if self.serial:
                cmd.extend(["-s", self.serial])
            cmd.extend(["shell", "input", "text", escaped])
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                return True
            logger.warning(f"ADB input text fallback returned code {result.returncode}")
        except Exception as e:
            logger.error(f"ADB input text fallback also failed: {e}")
        return False

    def clear_focused(self) -> bool:
        """Clears text of the currently focused input element."""
        if self.mock:
            logger.info("[Mock] Clear focused element")
            return True
        if not self._ensure_connected():
            logger.error("Cannot clear focused element: connection lost.")
            return False
        try:
            focused_el = self.d(focused=True)
            if focused_el.wait(timeout=3.0):
                focused_el.clear_text()
                return True
            else:
                logger.warning("No focused element found within timeout, skipping clear.")
                return True  # Not a failure — just nothing to clear
        except Exception as e:
            logger.warning(f"Failed to clear focused element (non-fatal): {e}")
            return True  # Non-fatal — proceed with typing anyway

    def swipe_coordinates(self, fx: int, fy: int, tx: int, ty: int, duration_ms: int = 300) -> bool:
        """Performs swipe gesture from (fx, fy) to (tx, ty)."""
        if self.mock:
            logger.info(f"[Mock] Swipe from ({fx}, {fy}) to ({tx}, {ty}) in {duration_ms}ms")
            return True
        if not self._ensure_connected():
            logger.error("Cannot swipe: connection lost.")
            return False
        try:
            # uiautomator2 expects duration in seconds
            self.d.swipe(fx, fy, tx, ty, duration=duration_ms / 1000.0)
            return True
        except Exception as e:
            logger.error(f"Failed to swipe: {e}")
            if self.reconnect():
                try:
                    self.d.swipe(fx, fy, tx, ty, duration=duration_ms / 1000.0)
                    return True
                except Exception as e2:
                    logger.error(f"Retry swipe failed: {e2}")
            return False

    def app_current(self) -> Dict[str, Any]:
        """Returns the current foreground app package and activity."""
        if self.mock:
            return {
                "package": "com.android.settings",
                "activity": "com.android.settings.Settings"
            }
        if not self._ensure_connected():
            logger.error("Cannot get current app: connection lost.")
            return {"package": "", "activity": ""}
        try:
            curr = self.d.app_current()
            return {
                "package": curr.get("package", ""),
                "activity": curr.get("activity", "")
            }
        except Exception as e:
            logger.error(f"Failed to get current app: {e}")
            if self.reconnect():
                try:
                    curr = self.d.app_current()
                    return {
                        "package": curr.get("package", ""),
                        "activity": curr.get("activity", "")
                    }
                except Exception as e2:
                    logger.error(f"Retry get current app failed: {e2}")
            return {"package": "", "activity": ""}

    def get_screenshot_base64(self) -> Optional[str]:
        """Returns the base64 encoded PNG screenshot."""
        if self.mock:
            # 1x1 transparent pixel PNG base64
            return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        if not self._ensure_connected():
            logger.error("Cannot capture screenshot: connection lost.")
            return None
        try:
            img = self.d.screenshot()
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            if self.reconnect():
                try:
                    img = self.d.screenshot()
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    return base64.b64encode(buffered.getvalue()).decode("utf-8")
                except Exception as e2:
                    logger.error(f"Retry screenshot failed: {e2}")
            return None

    @property
    def window_size(self) -> Tuple[int, int]:
        """Returns the screen window size as (width, height)."""
        if self.mock:
            return (1080, 1920)
        if not self._ensure_connected():
            logger.error("Cannot get window size: connection lost.")
            return (1080, 1920)
        try:
            # uiautomator2 returns (width, height)
            w, h = self.d.window_size()
            return (w, h)
        except Exception as e:
            logger.error(f"Failed to get window size: {e}")
            if self.reconnect():
                try:
                    w, h = self.d.window_size()
                    return (w, h)
                except Exception as e2:
                    logger.error(f"Retry get window size failed: {e2}")
            return (1080, 1920)

    # --- High-level semantic actions for API route and manager compatibility ---
    def tap(self, element: Any) -> Dict[str, Any]:
        """High-level element tap adapter compatible with API route expectations."""
        # Extract bounds and element ID
        element_id = ""
        if isinstance(element, dict):
            bounds = element.get("bounds", {})
            left = bounds.get("left", 0)
            top = bounds.get("top", 0)
            right = bounds.get("right", 0)
            bottom = bounds.get("bottom", 0)
            element_id = element.get("id") or element.get("element_id") or ""
        elif hasattr(element, "bounds"):
            left = element.bounds.left
            top = element.bounds.top
            right = element.bounds.right
            bottom = element.bounds.bottom
            element_id = getattr(element, "element_id", getattr(element, "id", ""))
        else:
            logger.error(f"Invalid element object passed to tap: {type(element)}")
            return {"success": False}

        cx = (left + right) // 2
        cy = (top + bottom) // 2
        success = self.click(cx, cy)
        return {"success": success, "matched_element": element_id}

    def type_text(self, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """High-level type text adapter compatible with API route expectations."""
        if clear_first:
            self.clear_focused()
        success = self.send_keys(text)
        return {"success": success}

    def swipe_direction(self, direction: str, distance: int = 500, speed: int = 300) -> Dict[str, Any]:
        """High-level swipe adapter compatible with API route expectations."""
        from vrski.ui.actions import swipe as ui_swipe
        success = ui_swipe(self, direction, distance, speed)
        return {"success": success}

    # Override base swipe to support both (x,y)->(x,y) and direction swipe
    def swipe(self, *args, **kwargs) -> Any:
        """Adapts between low-level coordinate swipe and high-level direction swipe."""
        # If first argument is a string (direction), delegate to swipe_direction
        if len(args) > 0 and isinstance(args[0], str):
            return self.swipe_direction(*args, **kwargs)
        if "direction" in kwargs:
            return self.swipe_direction(**kwargs)
        # Otherwise delegate to low-level swipe coordinates
        return self.swipe_coordinates(*args, **kwargs)

    def scroll_to(self, text: str) -> Dict[str, Any]:
        """High-level scroll_to adapter compatible with API route expectations."""
        from vrski.ui.actions import scroll_to_text as ui_scroll_to_text
        success, found = ui_scroll_to_text(self, text)
        return {"success": success, "found": found}


    def connect(self, serial: Optional[str] = None) -> None:
        """Connects or reconnects to the device."""
        if serial:
            self.serial = serial
        if self.mock:
            logger.info(f"[Mock] Connected (serial: {self.serial or 'default'})")
            return
        if not self.d or not self.is_connected():
            self.reconnect()

    def find_by_text(self, text: str, exact: bool = False) -> Optional[UIElement]:
        """Finds the first element matching the given text."""
        from vrski.ui.finder import find_first
        elements = self.get_tree()
        return find_first(elements, text=text, exact=exact)

    def find_by_id(self, element_id: str, exact: bool = False) -> Optional[UIElement]:
        """Finds the first element matching the given resource-id."""
        from vrski.ui.finder import find_first
        elements = self.get_tree()
        return find_first(elements, element_id=element_id, exact=exact)

    def tap_element(self, element: Any) -> Dict[str, Any]:
        """Taps a UIElement by computing its center coordinates."""
        return self.tap(element)

    def type_into(self, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Types text into the currently focused element."""
        return self.type_text(text, clear_first=clear_first)

    def scroll_to_text(self, text: str, max_swipes: int = 10) -> Dict[str, Any]:
        """Scrolls until the specified text is visible on screen."""
        from vrski.ui.actions import scroll_to_text as _scroll_to_text
        success, found = _scroll_to_text(self, text, max_swipes=max_swipes)
        return {"success": success, "found": found}


# Define UIDriver alias so manager.py import succeeds
UIDriver = DeviceDriver


