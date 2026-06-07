import os
import time
import logging
import base64
from typing import Dict, Any
from vrski.session.manager import SessionManager
from vrski.ui.actions import tap as ui_tap, type_text as ui_type

logger = logging.getLogger("vrski.playstore.installer")

def install_app(session_id: str, package_name: str) -> Dict[str, Any]:
    """
    Automates searching and installing an app from the Google Play Store.
    """
    start_time = time.time()

    # Determine if simulated
    if SessionManager.is_simulated(session_id):
        time.sleep(1.0)  # brief simulation delay
        adb_client = SessionManager.get_adb_client(session_id)
        if adb_client and hasattr(adb_client, "installed_packages"):
            adb_client.installed_packages.add(package_name)
        duration = round(time.time() - start_time, 2)
        return {
            "success": True,
            "package_name": package_name,
            "duration_seconds": duration,
            "error": None
        }

    driver = SessionManager.get_driver(session_id)
    adb_client = SessionManager.get_adb_client(session_id)
    if not driver or not adb_client:
        return {
            "success": False,
            "package_name": package_name,
            "duration_seconds": 0.0,
            "error": "Session driver or ADB client not initialized"
        }

    # Helper for failures
    def failure_result(err_msg: str) -> dict:
        screenshot_b64 = None
        try:
            temp_path = f"tmp_install_fail_{session_id}.png"
            if adb_client.screenshot(temp_path):
                with open(temp_path, "rb") as f:
                    screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")
                os.remove(temp_path)
        except Exception as e:
            logger.error(f"Failed to capture screenshot during install failure: {e}")
        return {
            "success": False,
            "package_name": package_name,
            "duration_seconds": round(time.time() - start_time, 2),
            "error": err_msg,
            "screenshot_base64": screenshot_b64
        }

    # 1. Check if already installed
    try:
        if adb_client.is_installed(package_name):  # checks adb shell pm list packages | grep {package}
            logger.info(f"App {package_name} is already installed.")
            return {
                "success": True,
                "package_name": package_name,
                "duration_seconds": 0.0,
                "error": None
            }
    except Exception as e:
        logger.error(f"Failed to check if package is installed: {e}")

    try:
        # 2. Launch Play Store
        logger.info("Opening Play Store...")
        adb_client.run_cmd(["shell", "am", "start", "-n", "com.android.vending/.AssetBrowserActivity"])
        time.sleep(2.0)

        # 3. Locate search bar
        tree = driver.get_tree()
        
        # If there is a bottom Search tab, tap it first
        search_tab = next((el for el in tree if getattr(el, "text", "") == "Search" and getattr(el, "bounds", None) and el.bounds.top > 2000), None)
        if search_tab:
            logger.info("Found bottom Search tab, tapping it...")
            if getattr(search_tab, "element_id", ""):
                ui_tap(driver, element_id=search_tab.element_id)
            else:
                driver.tap(search_tab)
            time.sleep(2.0)
            tree = driver.get_tree()

        # Find the search input field near the top
        search_field = next((el for el in tree if ("search" in str(getattr(el, "text", "")).lower() or "search" in str(getattr(el, "content_desc", "")).lower()) and getattr(el, "bounds", None) and el.bounds.top < 500), None)
        
        if not search_field:
            # Fallback to click somewhere in the top region
            logger.info("Could not find explicit search field, tapping top of screen...")
            driver.click(500, 100)
            time.sleep(1.0)
            tree = driver.get_tree()
            search_field = next((el for el in tree if getattr(el, "editable", False) or "search" in str(getattr(el, "text", "")).lower()), None)

        if not search_field:
            return failure_result("Could not locate search text input field in Play Store")

        # Tap search bar and type package name
        logger.info("Tapping search bar...")
        if getattr(search_field, "element_id", ""):
            ui_tap(driver, element_id=search_field.element_id)
        else:
            driver.tap(search_field)
            
        ui_type(driver, package_name, clear_first=True)
        time.sleep(1.5)

        # Submit search query using KEYCODE_ENTER (66)
        logger.info(f"Submitting search query for {package_name}...")
        adb_client.key_event(66)
        time.sleep(3.0)

        # 4. Find the Install button on the search results or detail page
        tree = driver.get_tree()
        
        # Look for "Install" / "Update" / "Enable" button (do not enforce clickable flag)
        install_btn = next((el for el in tree if getattr(el, "text", "") in ["Install", "Update", "Enable"]), None)
        
        if not install_btn:
            # Maybe we need to click the search result first to open the app page
            logger.info("Install button not directly visible. Searching for result list item...")
            parts = package_name.split(".")
            keyword = parts[-1] if len(parts) > 1 else package_name
            result_item = next((el for el in tree if (keyword.lower() in str(getattr(el, "text", "")).lower() or keyword.lower() in str(getattr(el, "content_desc", "")).lower())), None)
            
            if result_item:
                logger.info(f"Tapping search result item: {getattr(result_item, 'text', '') or getattr(result_item, 'content_desc', '')}")
                driver.tap(result_item)
                time.sleep(3.0)
                tree = driver.get_tree()
                install_btn = next((el for el in tree if getattr(el, "text", "") in ["Install", "Update", "Enable"]), None)

        if not install_btn:
            return failure_result("Could not locate 'Install' button for the target package")

        # 5. Click Install — tap center coords directly (handles clickable=False TextViews
        #    where the real clickable is a parent View wrapping the same area)
        logger.info("Tapping 'Install' button...")
        bounds = getattr(install_btn, "bounds", None)
        if bounds:
            cx = (bounds.left + bounds.right) // 2
            cy = (bounds.top + bounds.bottom) // 2
            driver.click(cx, cy)
        elif getattr(install_btn, "element_id", ""):
            ui_tap(driver, element_id=install_btn.element_id)
        else:
            driver.tap(install_btn)
        time.sleep(3.0)

        # 6. Poll for installation completion (300s — accounts for large apps on slow links)
        logger.info(f"Polling for installation completion of {package_name}...")
        max_wait_s = 300
        poll_interval_s = 5
        elapsed = 0

        while elapsed < max_wait_s:
            if adb_client.is_installed(package_name):
                duration = round(time.time() - start_time, 2)
                logger.info(f"App {package_name} installed successfully in {duration}s.")
                return {
                    "success": True,
                    "package_name": package_name,
                    "duration_seconds": duration,
                    "error": None
                }
            # Log progress visible in Play Store ("X% of Y MB") for debugging
            try:
                tree = driver.get_tree()
                progress = next((el for el in tree if "% of" in str(getattr(el, "text", ""))), None)
                if progress:
                    logger.info(f"Download progress: {progress.text}")
                # Detect "Cancel" = download is active; keep waiting
                cancel = next((el for el in tree if getattr(el, "text", "") == "Cancel"), None)
                if cancel:
                    logger.info("Download in progress (Cancel button visible)...")
            except Exception:
                pass
            time.sleep(poll_interval_s)
            elapsed += poll_interval_s

        return failure_result(f"Installation timed out after {max_wait_s} seconds")

    except Exception as e:
        logger.exception("Error executing Play Store installation")
        return failure_result(f"Exception during installation: {str(e)}")
