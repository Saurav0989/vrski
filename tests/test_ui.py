import os
import tempfile
import base64
import pytest
from vrski.ui.element import Bounds, UIElement
from vrski.adb.client import ADBClient
from vrski.ui.driver import DeviceDriver, parse_bounds
from vrski.ui.finder import find_elements, find_first
from vrski.ui.actions import (
    tap,
    type_text,
    swipe,
    scroll_to_text,
    press_back,
    press_home,
    press_recent_apps
)

# Set mock environment variable for tests
os.environ["VRSKI_MOCK"] = "1"

def test_bounds_and_element():
    bounds = Bounds(left=10, top=20, right=110, bottom=120)
    assert bounds.center_x == 60
    assert bounds.center_y == 70
    
    data = bounds.to_dict()
    assert data == {"left": 10, "top": 20, "right": 110, "bottom": 120}
    
    restored_bounds = Bounds.from_dict(data)
    assert restored_bounds.left == 10
    assert restored_bounds.right == 110

    element = UIElement(
        element_id="com.example:id/button",
        element_type="Button",
        text="Click Me",
        content_desc="ActionButton",
        clickable=True,
        scrollable=False,
        editable=False,
        bounds=bounds
    )
    
    el_dict = element.to_dict()
    assert el_dict["id"] == "com.example:id/button"
    assert el_dict["type"] == "Button"
    assert el_dict["text"] == "Click Me"
    assert el_dict["bounds"]["left"] == 10

    restored_el = UIElement.from_dict(el_dict)
    assert restored_el.element_id == "com.example:id/button"
    assert restored_el.element_type == "Button"
    assert restored_el.text == "Click Me"
    assert restored_el.clickable is True
    assert restored_el.bounds.center_x == 60

def test_adb_client_mock():
    client = ADBClient(mock=True)
    assert client.mock is True
    
    # Test list packages
    packages = client.list_packages()
    assert "com.android.settings" in packages
    assert "com.whatsapp" in packages
    
    # Test installation checks
    assert client.is_installed("com.whatsapp") is True
    assert client.is_installed("com.notinstalled") is False
    
    # Test install / uninstall / launch / stop
    assert client.install_apk("dummy.apk") is True
    assert client.launch_package("com.whatsapp") is True
    assert client.force_stop("com.whatsapp") is True
    assert client.uninstall_package("com.whatsapp") is True
    assert client.is_installed("com.whatsapp") is False
    
    # Test key events
    assert client.key_back() is True
    assert client.key_home() is True
    assert client.key_recent_apps() is True
    assert client.key_event(66) is True
    assert client.raw_tap(100, 200) is True

    # Test screenshot
    with tempfile.TemporaryDirectory() as tmpdir:
        screenshot_path = os.path.join(tmpdir, "screen.png")
        assert client.screenshot(screenshot_path) is True
        assert os.path.exists(screenshot_path)
        with open(screenshot_path, "rb") as f:
            content = f.read()
            # Verify PNG signature
            assert content.startswith(b"\x89PNG")

def test_parse_bounds():
    assert parse_bounds(None) is None
    assert parse_bounds("") is None
    assert parse_bounds("invalid") is None
    
    b = parse_bounds("[10,20][30,40]")
    assert b is not None
    assert b.left == 10
    assert b.top == 20
    assert b.right == 30
    assert b.bottom == 40
    
    # Negative coordinate bounds
    b_neg = parse_bounds("[-10,-20][-5,-5]")
    assert b_neg is not None
    assert b_neg.left == -10
    assert b_neg.top == -20
    assert b_neg.right == -5
    assert b_neg.bottom == -5

def test_device_driver_mock():
    driver = DeviceDriver(mock=True)
    assert driver.mock is True
    
    # Test window size
    assert driver.window_size == (1080, 1920)
    
    # Test mock hierarchy tree parsing
    tree = driver.get_tree()
    assert len(tree) > 0
    
    # Find settings title in default mock XML
    settings_title = next((el for el in tree if el.text == "Settings"), None)
    assert settings_title is not None
    assert settings_title.element_id == "android:id/title"
    assert settings_title.element_type == "TextView"
    assert settings_title.clickable is False
    assert settings_title.bounds.left == 32
    
    # Find editable field
    search_bar = next((el for el in tree if el.element_type == "EditText"), None)
    assert search_bar is not None
    assert search_bar.editable is True
    assert search_bar.text == "Search settings"
    
    # Test click / keys / swipe / current app
    assert driver.click(100, 200) is True
    assert driver.send_keys("Hello") is True
    assert driver.clear_focused() is True
    assert driver.swipe(0, 0, 100, 100) is True
    
    curr = driver.app_current()
    assert curr["package"] == "com.android.settings"
    
    # Test screenshot base64
    sb64 = driver.get_screenshot_base64()
    assert sb64 is not None
    # Ensure it's valid base64 PNG
    img_data = base64.b64decode(sb64)
    assert img_data.startswith(b"\x89PNG")

def test_finder():
    driver = DeviceDriver(mock=True)
    tree = driver.get_tree()
    
    # Case insensitive substring find
    matches = find_elements(tree, text="network")
    assert len(matches) == 1
    assert matches[0].text == "Network & internet"
    
    # Exact find
    assert find_first(tree, text="network", exact=True) is None
    assert find_first(tree, text="Network & internet", exact=True) is not None
    
    # Find by ID
    bluetooth_btn = find_first(tree, element_id="com.android.settings:id/bluetooth_option")
    assert bluetooth_btn is not None
    assert bluetooth_btn.text == "Bluetooth"
    
    # Find by clickable
    clickable_elements = find_elements(tree, clickable=True)
    assert len(clickable_elements) == 4  # Network, Connected, Bluetooth, Search
    
    # No matches
    assert find_first(tree, text="Nonexistent") is None

def test_actions_tap():
    driver = DeviceDriver(mock=True)
    
    # Tap by coordinates
    success, el = tap(driver, x=150, y=250)
    assert success is True
    assert el is None
    
    # Tap by text
    success, el = tap(driver, text="Bluetooth")
    assert success is True
    assert el is not None
    assert el.text == "Bluetooth"
    assert el.bounds.center_x == (64 + 1000) // 2
    
    # Tap nonexistent
    success, el = tap(driver, text="Nonexistent")
    assert success is False
    assert el is None

def test_actions_type_and_keypresses():
    driver = DeviceDriver(mock=True)
    
    assert type_text(driver, "Query", clear_first=True) is True
    assert press_back(driver) is True
    assert press_home(driver) is True
    assert press_recent_apps(driver) is True

def test_actions_swipe():
    driver = DeviceDriver(mock=True)
    
    assert swipe(driver, direction="up") is True
    assert swipe(driver, direction="down", distance=200, speed_ms=150) is True
    assert swipe(driver, direction="left") is True
    assert swipe(driver, direction="right") is True
    assert swipe(driver, direction="invalid") is False

def test_actions_scroll_to_text():
    driver = DeviceDriver(mock=True)
    
    # Already visible text
    success, found = scroll_to_text(driver, "Settings")
    assert success is True
    assert found is True
    
    # Dynamic scroll-to test where element appears after 2 swipes
    driver.set_mock_xml("""<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]">
    <node index="0" text="Settings" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[32,80][300,150]"/>
  </node>
</hierarchy>
""")
    
    original_swipe = driver.swipe
    swipe_count = 0
    
    def tracking_swipe(fx, fy, tx, ty, duration_ms=300):
        nonlocal swipe_count
        swipe_count += 1
        if swipe_count == 1:
            driver.set_mock_xml("""<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]">
    <node index="0" text="Settings Page 2" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[32,80][300,150]"/>
  </node>
</hierarchy>
""")
        elif swipe_count == 2:
            driver.set_mock_xml("""<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]">
    <node index="0" text="Target Found!" resource-id="com.android.settings:id/target" class="android.widget.TextView" package="com.android.settings" bounds="[64,400][1000,500]"/>
  </node>
</hierarchy>
""")
        return original_swipe(fx, fy, tx, ty, duration_ms)
        
    driver.swipe = tracking_swipe
    
    success, found = scroll_to_text(driver, "Target Found!", max_swipes=5)
    assert success is True
    assert found is True
    assert swipe_count == 2

def test_actions_scroll_to_not_found():
    driver = DeviceDriver(mock=True)
    driver.set_mock_xml("""<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.settings" bounds="[0,0][1080,1920]">
    <node index="0" text="Static Content" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" bounds="[32,80][300,150]"/>
  </node>
</hierarchy>
""")
    
    # If the content is static and doesn't change after swiping, it should exit early
    success, found = scroll_to_text(driver, "Never Appears", max_swipes=5)
    assert success is True
    assert found is False

def test_malformed_bounds_normalization():
    # Test coordinates that are out of order
    b = Bounds(left=100, top=200, right=50, bottom=100)
    assert b.left == 50
    assert b.right == 100
    assert b.top == 100
    assert b.bottom == 200
    
    # Test negative coordinate clamping for center calculation
    b_neg = Bounds(left=-100, top=-200, right=-50, bottom=-100)
    assert b_neg.center_x == 0
    assert b_neg.center_y == 0

def test_driver_connection_lifecycle():
    driver = DeviceDriver(mock=True)
    assert driver.is_connected() is True
    assert driver.reconnect() is True
    assert driver._ensure_connected() is True

def test_adb_client_timeout():
    import subprocess
    from unittest.mock import patch
    
    client = ADBClient(mock=False)
    
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["adb", "shell"], timeout=20)
        res = client.run_cmd(["shell"], timeout=20)
        assert res.returncode == -1
        assert "TimeoutExpired" in res.stderr

def test_ui_tap_empty_args():
    driver = DeviceDriver(mock=True)
    success, el = tap(driver)
    assert success is False
    assert el is None

def test_driver_malformed_xml():
    driver = DeviceDriver(mock=True)
    driver.set_mock_xml("<malformed xml")
    tree = driver.get_tree()
    assert tree == []

def test_adb_client_command_failures():
    from unittest.mock import patch
    import subprocess
    client = ADBClient(mock=False)
    
    with patch("subprocess.run") as mock_run:
        # 1. Install failure
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "install"],
            returncode=1,
            stdout="",
            stderr="Failure [INSTALL_FAILED_ALREADY_EXISTS]"
        )
        assert client.install_apk("some.apk") is False
        
        # 2. Uninstall failure
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "uninstall"],
            returncode=1,
            stdout="",
            stderr="Failure [DELETE_FAILED_INTERNAL_ERROR]"
        )
        assert client.uninstall_package("some.package") is False

        # 3. Launch package failure
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "monkey"],
            returncode=1,
            stdout="",
            stderr="monkey failed"
        )
        assert client.launch_package("some.package") is False

        # 4. List packages failure
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "pm", "list"],
            returncode=1,
            stdout="",
            stderr="pm list failed"
        )
        assert client.list_packages() == []


if __name__ == "__main__":
    import time
    # Force real connection
    os.environ["VRSKI_MOCK"] = "0"
    
    # 1. Launch Settings
    adb_client = ADBClient(mock=False)
    adb_client.force_stop("com.android.settings")
    time.sleep(1.0)
    adb_client.run_cmd(["shell", "am", "start", "-n", "com.android.settings/.Settings"])
    time.sleep(2.5)
    
    # 2. Call get_tree()
    d = DeviceDriver(mock=False)
    d.connect()
    t = d.get_tree()
    assert len(t) > 0, "No elements found on Settings screen"
    
    # 3. Find by text
    target = None
    for label in ['Network', 'Bluetooth', 'Display', 'Battery', 'Apps', 'Notifications', 'Sound']:
        target = d.find_by_text(label)
        if target:
            break
    assert target is not None, "Could not find a valid Settings header to tap"
    
    # 4. Tap element
    d.tap_element(target)
    time.sleep(2.0)
    
    # 5. Assert elements differ
    t2 = d.get_tree()
    assert [e.text for e in t if e.text] != [e.text for e in t2 if e.text], "Screen did not change after tap"
    
    # 6. Print success
    print("PHASE 1: ALL PASS")


