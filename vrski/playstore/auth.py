import os
import re
import time
import logging
import base64
from typing import Optional, Dict, Any, Tuple
from vrski.session.manager import SessionManager
from vrski.ui.actions import tap as ui_tap, type_text as ui_type

logger = logging.getLogger("vrski.playstore.auth")

def get_playstore_account(session_id: str) -> Dict[str, Any]:
    """
    Checks if a Google account is currently signed in on the emulator/device.
    Returns:
        {"signed_in": bool, "account": str | None}
    """
    if SessionManager.is_simulated(session_id):
        # In simulated mode, default to the test account
        return {"signed_in": True, "account": "vrski.agent@gmail.com"}

    adb_client = SessionManager.get_adb_client(session_id)
    if not adb_client:
        return {"signed_in": False, "account": None}

    try:
        # Query primary registered accounts on the Android device
        result = adb_client.run_cmd(["shell", "dumpsys", "account"])
        output = result.stdout
        if isinstance(output, bytes):
            output = output.decode("utf-8")

        # Typical format: Account {name=user@gmail.com, type=com.google}
        google_accounts = re.findall(r"name=([a-zA-Z0-9._%+-]+@gmail\.com)", output)
        if google_accounts:
            return {"signed_in": True, "account": google_accounts[0]}

        # Fallback to find any gmail string
        gmail_matches = re.findall(r"[a-zA-Z0-9._%+-]+@gmail\.com", output)
        if gmail_matches:
            return {"signed_in": True, "account": gmail_matches[0]}

    except Exception as e:
        logger.error(f"Error checking signed-in Google account: {e}")

    return {"signed_in": False, "account": None}


def poll_for_element_conditions(driver, timeout_s: float = 15.0) -> Tuple[Optional[str], list]:
    """Polls the UI tree to identify sign-in state or inputs."""
    start_time = time.time()
    while time.time() - start_time < timeout_s:
        tree = driver.get_tree()
        
        # 1. Check if signed in / search bar visible
        search_bar = next((el for el in tree if "search_bar" in str(getattr(el, "element_id", "")).lower() or "search" in str(getattr(el, "text", "")).lower()), None)
        if search_bar:
            return "search_bar_visible", tree
            
        # 2. Check for "Sign in" button
        signin_btn = next((el for el in tree if getattr(el, "text", "") == "Sign in"), None)
        if signin_btn:
            return "signin_button_visible", tree

        # 3. Check for Gmail input field (Google login screen)
        # Standard ID: identifierId
        email_input = next((el for el in tree if "identifierid" in str(getattr(el, "element_id", "")).lower() or (getattr(el, "editable", False) and "email" in str(getattr(el, "text", "")).lower())), None)
        if email_input:
            return "email_input_visible", tree

        # 4. Check for Password input field
        # Standard ID: password (or type is password)
        pwd_input = next((el for el in tree if "password" in str(getattr(el, "element_id", "")).lower() or (getattr(el, "editable", False) and "password" in str(getattr(el, "content_desc", "")).lower())), None)
        if pwd_input:
            return "password_input_visible", tree

        # 5. Check for Google terms / agree screens
        agree_btn = next((el for el in tree if getattr(el, "text", "") in ["I agree", "Agree", "Accept"]), None)
        if agree_btn:
            return "agree_button_visible", tree

        # 6. Check for CAPTCHA presence
        captcha = next((el for el in tree if "captcha" in str(getattr(el, "text", "")).lower() or "captcha" in str(getattr(el, "element_id", "")).lower()), None)
        if captcha:
            return "captcha_detected", tree

        time.sleep(1.0)
    return None, driver.get_tree()


# Dismissal labels in PREFERENCE order: grant permissions so the app works,
# then neutral acknowledgements, then "later/skip" style, and only as a last
# resort negative answers. Matched against an element's text OR content_desc
# (case-insensitive, exact). Deliberately excludes destructive labels
# (Delete/Remove/Uninstall/etc.) so we never tap something harmful.
SAFE_DISMISS_LABELS = [
    "allow", "allow all", "while using the app", "only this time",
    "got it", "ok", "okay", "continue", "accept", "accept all",
    "agree", "i agree", "no thanks", "no, thanks", "not now",
    "maybe later", "later", "skip", "skip for now", "dismiss", "close",
    "done", "don't allow", "deny",
]


def dismiss_popups(session_id: str, max_rounds: int = 3) -> bool:
    """Detects and dismisses blocking dialogs/overlays that interrupt automation.

    Handles permission prompts, coachmarks, "rate this app", update banners,
    onboarding acknowledgements, etc. Matches by text OR content_desc, taps via the
    element's center (so a label inside a clickable parent still works), and loops a
    few times to clear stacked dialogs. Never taps destructive labels.
    """
    driver = SessionManager.get_driver(session_id)
    if not driver or not hasattr(driver, "get_tree"):
        return False

    dismissed_any = False
    for _ in range(max_rounds):
        tree = driver.get_tree() or []
        # Index elements by their normalized label for preference-ordered lookup.
        by_label: Dict[str, Any] = {}
        for el in tree:
            label = (getattr(el, "text", "") or getattr(el, "content_desc", "") or "").strip().lower()
            if label and label not in by_label:
                by_label[label] = el

        target = next((by_label[l] for l in SAFE_DISMISS_LABELS if l in by_label), None)
        if not target:
            break

        shown = getattr(target, "text", "") or getattr(target, "content_desc", "")
        logger.info(f"Dismissing blocker: '{shown}'")
        try:
            driver.tap(target)  # center-tap handles labels nested in a clickable parent
            dismissed_any = True
        except Exception as e:
            logger.warning(f"Failed to tap blocker '{shown}': {e}")
            break
        time.sleep(0.6)

    return dismissed_any


def signin_playstore(session_id: str, gmail: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Signs into Google on the emulator using direct ADB injection (FastInputIME).

    No virtual keyboard, no accessibility-tree gymnastics for WebViews.
    If gmail/password are not provided, reads from .env (set via vrski_setup).
    """
    if not gmail or not password:
        try:
            from vrski.credentials import load_credentials
            saved_email, saved_password = load_credentials()
            gmail = gmail or saved_email
            password = password or saved_password
        except Exception:
            pass

    if not gmail or not password:
        return {
            "success": False,
            "error": (
                "No credentials provided and none found in .env. "
                "Call vrski_setup(session_id, email, password) first."
            ),
        }

    # Use the shell-based auth (FastInputIME + coordinates) as primary path
    try:
        from vrski.playstore.shell_auth import google_login_shell
        return google_login_shell(session_id, gmail, password)
    except Exception as e:
        logger.warning(f"shell_auth failed ({e}), falling back to legacy UI flow")

    if SessionManager.is_simulated(session_id):
        driver = SessionManager.get_driver(session_id)
        if driver and hasattr(driver, "current_screen"):
            driver.current_screen = "playstore"
        return {"success": True, "account": gmail, "error": None}

    driver = SessionManager.get_driver(session_id)
    adb_client = SessionManager.get_adb_client(session_id)
    if not driver or not adb_client:
        return {"success": False, "error": "Session driver or ADB client not initialized"}

    # Capture helper for screenshots on failure
    def failure_result(err_msg: str) -> dict:
        screenshot_b64 = None
        try:
            temp_path = f"tmp_auth_fail_{session_id}.png"
            if adb_client.screenshot(temp_path):
                with open(temp_path, "rb") as f:
                    screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")
                os.remove(temp_path)
        except Exception as e:
            logger.error(f"Failed to capture screenshot during auth failure: {e}")
        return {"success": False, "error": err_msg, "screenshot_base64": screenshot_b64}

    try:
        # Step 1: Force stop and launch Play Store (fresh state)
        logger.info("Killing and relaunching Google Play Store...")
        adb_client.force_stop("com.android.vending")
        time.sleep(1.5)
        
        # Launch using play store main activity
        launch_res = adb_client.run_cmd(["shell", "am", "start", "-n", "com.android.vending/.AssetBrowserActivity"])
        if launch_res.returncode != 0:
            return failure_result("Failed to start Google Play Store activity")

        # Step 2: Poll for initial state (Sign-in page vs Logged-in Home)
        state, tree = poll_for_element_conditions(driver, timeout_s=15.0)
        
        if state == "search_bar_visible":
            logger.info("Play Store already signed in.")
            current_acc = get_playstore_account(session_id)
            return {"success": True, "account": current_acc.get("account") or gmail, "error": None}

        if state == "signin_button_visible":
            logger.info("Clicking 'Sign in' button...")
            success, _ = ui_tap(driver, text="Sign in")
            if not success:
                return failure_result("Failed to tap 'Sign in' button")
            # Wait for login fields screen
            state, tree = poll_for_element_conditions(driver, timeout_s=15.0)

        # Step 3: Handle Email Entry
        if state == "email_input_visible" or any("email" in str(getattr(el, "text", "")).lower() for el in tree):
            logger.info("Entering Gmail username...")
            # Find input field
            email_field = next((el for el in tree if getattr(el, "editable", False)), None)
            if not email_field:
                return failure_result("Could not find editable email input field")
            
            # Tap it and type email
            ui_tap(driver, element_id=email_field.element_id)
            ui_type(driver, gmail, clear_first=True)
            time.sleep(0.5)
            
            # Click Next
            success, _ = ui_tap(driver, text="Next")
            if not success:
                # Fallback to look for content desc or any clickable button named Next/next
                success, _ = ui_tap(driver, content_desc="Next")
                
            if not success:
                return failure_result("Failed to proceed after typing Gmail username")
                
            state, tree = poll_for_element_conditions(driver, timeout_s=15.0)

        if state == "captcha_detected":
            return failure_result("captcha_detected")

        # Step 4: Handle Password Entry
        if state == "password_input_visible" or any("password" in str(getattr(el, "content_desc", "")).lower() for el in tree):
            logger.info("Entering Gmail password...")
            pwd_field = next((el for el in tree if getattr(el, "editable", False)), None)
            if not pwd_field:
                return failure_result("Could not find editable password input field")
                
            ui_tap(driver, element_id=pwd_field.element_id)
            ui_type(driver, password, clear_first=True)
            time.sleep(0.5)
            
            success, _ = ui_tap(driver, text="Next")
            if not success:
                success, _ = ui_tap(driver, content_desc="Next")
            if not success:
                return failure_result("Failed to proceed after typing password")
                
            state, tree = poll_for_element_conditions(driver, timeout_s=15.0)

        # Step 5: Handle Post-auth Agreements/Confirmations
        for attempt in range(5):
            if state == "agree_button_visible":
                logger.info("Tapping Agree/Accept button...")
                agree_btn = next((el for el in tree if getattr(el, "text", "") in ["I agree", "Agree", "Accept"]), None)
                if agree_btn:
                    ui_tap(driver, text=agree_btn.text)
                time.sleep(2.0)
                state, tree = poll_for_element_conditions(driver, timeout_s=10.0)
            elif state == "search_bar_visible":
                logger.info("Successfully signed in and reached Play Store main screen.")
                break
            else:
                # Look for other common skip buttons like "No thanks", "Skip", "Not now"
                skip_btn = next((el for el in tree if getattr(el, "text", "") in ["No thanks", "Skip", "Not now"]), None)
                if skip_btn:
                    logger.info(f"Tapping skip option: {skip_btn.text}")
                    ui_tap(driver, text=skip_btn.text)
                    time.sleep(2.0)
                    state, tree = poll_for_element_conditions(driver, timeout_s=10.0)
                else:
                    break

        # Confirm signed in
        if state == "search_bar_visible":
            current_acc = get_playstore_account(session_id)
            return {"success": True, "account": current_acc.get("account") or gmail, "error": None}
            
        # Last check if we are on search screen
        tree = driver.get_tree()
        if any("search" in str(getattr(el, "text", "")).lower() for el in tree):
            return {"success": True, "account": gmail, "error": None}

        return failure_result(f"Sign-in flow failed. Settled on unexpected screen state: {state}")

    except Exception as e:
        logger.exception("Error executing Play Store sign-in")
        return failure_result(f"Exception during authentication: {str(e)}")
