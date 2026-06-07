import logging
import time
from typing import Optional, Tuple, List
from vrski.ui.driver import DeviceDriver
from vrski.ui.element import UIElement
from vrski.ui.finder import find_first

logger = logging.getLogger("vrski.ui.actions")

def tap(
    driver: DeviceDriver,
    text: Optional[str] = None,
    element_id: Optional[str] = None,
    content_desc: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    exact: bool = False
) -> Tuple[bool, Optional[UIElement]]:
    """
    Taps a UI element by text, resource ID, content description, or raw coordinates.
    
    If raw coordinates (x, y) are provided, taps them directly.
    Otherwise, searches for the element and taps its center.
    
    Returns:
        A tuple of (success_boolean, matched_UIElement_or_None).
    """
    if x is not None and y is not None:
        logger.info(f"Tapping raw coordinates ({x}, {y})")
        success = driver.click(x, y)
        return success, None

    if text is None and element_id is None and content_desc is None:
        logger.warning("Failed to tap: no coordinates or identifier specified")
        return False, None

    # Retrieve tree and find element
    elements = driver.get_tree()
    target = find_first(
        elements=elements,
        text=text,
        element_id=element_id,
        content_desc=content_desc,
        exact=exact
    )

    if not target:
        logger.warning(
            f"Failed to find element for tap (text={text}, id={element_id}, desc={content_desc})"
        )
        return False, None

    cx = target.bounds.center_x
    cy = target.bounds.center_y
    logger.info(
        f"Tapping element '{target.text or target.content_desc or target.element_id}' at ({cx}, {cy})"
    )
    success = driver.click(cx, cy)
    return success, target

def type_text(driver: DeviceDriver, text: str, clear_first: bool = True) -> bool:
    """
    Types text into the currently focused field.
    
    Args:
        driver: The DeviceDriver instance.
        text: The string to type.
        clear_first: If True, clears the field before typing.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info(f"Typing text: '{text}' (clear_first={clear_first})")
    if clear_first:
        success_clear = driver.clear_focused()
        if not success_clear:
            logger.warning("Failed to clear focused element, continuing to type anyway")
            
    return driver.send_keys(text)

def swipe(
    driver: DeviceDriver,
    direction: str,
    distance: int = 500,
    speed_ms: int = 300
) -> bool:
    """
    Swipes in the given direction (up, down, left, right).
    
    Args:
        driver: The DeviceDriver instance.
        direction: 'up', 'down', 'left', or 'right'.
        distance: Distance in pixels.
        speed_ms: Speed/duration of swipe in milliseconds.
        
    Returns:
        True if successful, False otherwise.
    """
    w, h = driver.window_size
    direction = direction.lower()
    
    # Calculate start and end coordinates, clamping to screen boundaries
    margin = 50
    if direction == "up":
        # Swipe up moves screen down (drags from bottom to top)
        start_x = w // 2
        start_y = min(h - margin, h // 2 + distance // 2)
        end_x = w // 2
        end_y = max(margin, h // 2 - distance // 2)
    elif direction == "down":
        # Swipe down moves screen up (drags from top to bottom)
        start_x = w // 2
        start_y = max(margin, h // 2 - distance // 2)
        end_x = w // 2
        end_y = min(h - margin, h // 2 + distance // 2)
    elif direction == "left":
        # Swipe left moves screen right (drags from right to left)
        start_x = min(w - margin, w // 2 + distance // 2)
        start_y = h // 2
        end_x = max(margin, w // 2 - distance // 2)
        end_y = h // 2
    elif direction == "right":
        # Swipe right moves screen left (drags from left to right)
        start_x = max(margin, w // 2 - distance // 2)
        start_y = h // 2
        end_x = min(w - margin, w // 2 + distance // 2)
        end_y = h // 2
    else:
        logger.error(f"Invalid swipe direction: {direction}")
        return False

    logger.info(f"Swiping {direction} from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {speed_ms}ms")
    return driver.swipe(start_x, start_y, end_x, end_y, duration_ms=speed_ms)

def scroll_to_text(driver: DeviceDriver, text: str, max_swipes: int = 10) -> Tuple[bool, bool]:
    """
    Scrolls the screen (by swiping up) until the specified text is visible.
    
    Returns:
        A tuple of (success_boolean, found_boolean).
        - success_boolean: whether the scrolling actions completed without error.
        - found_boolean: whether the element with the target text was found.
    """
    logger.info(f"Scrolling to find text: '{text}' (max_swipes={max_swipes})")
    
    # First check if already visible
    elements = driver.get_tree()
    target = find_first(elements, text=text)
    if target:
        logger.info(f"Text '{text}' is already visible")
        return True, True

    last_xml = driver.get_hierarchy_xml()
    
    for i in range(max_swipes):
        logger.info(f"Scroll swipe {i+1}/{max_swipes}")
        # Swipe up (drags bottom to top) to scroll down
        success = swipe(driver, direction="up", distance=600, speed_ms=300)
        if not success:
            logger.error("Swipe action failed during scroll")
            return False, False
            
        # Add a short delay for screen to settle
        time.sleep(0.5)
        
        # Check if text is now visible
        elements = driver.get_tree()
        target = find_first(elements, text=text)
        if target:
            logger.info(f"Found text '{text}' after {i+1} swipes")
            return True, True
            
        # Detect if we have hit the bottom (hierarchy XML doesn't change after swipe)
        current_xml = driver.get_hierarchy_xml()
        if current_xml == last_xml:
            logger.info("Hierarchy did not change after swipe. Reached end of scrollable area.")
            break
        last_xml = current_xml

    logger.warning(f"Text '{text}' not found after scrolling")
    return True, False

def press_back(driver: DeviceDriver) -> bool:
    """Sends a back keypress event."""
    if driver.mock:
        logger.info("[Mock] Pressing BACK key")
        return True
    try:
        driver.d.press("back")
        return True
    except Exception as e:
        logger.error(f"Failed to press BACK: {e}")
        return False

def press_home(driver: DeviceDriver) -> bool:
    """Sends a home keypress event."""
    if driver.mock:
        logger.info("[Mock] Pressing HOME key")
        return True
    try:
        driver.d.press("home")
        return True
    except Exception as e:
        logger.error(f"Failed to press HOME: {e}")
        return False

def press_recent_apps(driver: DeviceDriver) -> bool:
    """Sends a recent apps keypress event."""
    if driver.mock:
        logger.info("[Mock] Pressing RECENT_APPS key")
        return True
    try:
        driver.d.press("recent")
        return True
    except Exception as e:
        logger.error(f"Failed to press RECENT_APPS: {e}")
        return False
