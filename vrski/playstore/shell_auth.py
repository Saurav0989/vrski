"""
Optional agent-assisted Google sign-in helper.

This auto-fills the email and password on the Google sign-in screen by:
  1. Finding the native EditText element in the UI tree (the GMS sign-in screen
     exposes real EditText nodes, not just an opaque WebView).
  2. Tapping its center, then injecting text with `adb shell input text`, which
     dispatches KeyEvents directly to the focused view — handles '@' and '.'
     natively, no IME switching, no base64 broadcasts.

IMPORTANT LIMITATION — Google 2-Step Verification:
  After the password, Google usually shows a "Verify it's you" challenge that
  requires tapping a number on the owner's trusted phone. No automation can pass
  this. When that happens, this helper returns success=False with
  error="2fa_required" so the caller can ask the human to finish (or use the
  human-driven scripts/login.sh instead, which is the recommended path).
"""
import time
import logging
import subprocess
from typing import Dict, Any, Optional
from vrski.session.manager import SessionManager
from vrski.playstore.auth import get_playstore_account

logger = logging.getLogger("vrski.playstore.shell_auth")


def _adb_input_text(serial: str, text: str) -> None:
    """Inject text via KeyEvents to the focused view. Works on WebView fields."""
    base = ["adb"]
    if serial:
        base.extend(["-s", serial])
    # `input text` needs spaces escaped as %s; other chars in emails/passwords
    # (@ . - _ digits letters) are handled by the KeyCharacterMap.
    safe = text.replace(" ", "%s")
    subprocess.run(base + ["shell", "input", "text", safe],
                   capture_output=True, timeout=15)


def _find_editable(tree) -> Optional[Any]:
    """Return the first editable EditText element in the tree, if any."""
    for el in tree:
        cls = str(getattr(el, "class_name", "") or getattr(el, "type", ""))
        if getattr(el, "editable", False) or cls.endswith("EditText"):
            if getattr(el, "bounds", None):
                return el
    return None


def _find_text(tree, *labels) -> Optional[Any]:
    """Return the first element whose text matches any of labels (case-insensitive)."""
    wanted = {l.lower() for l in labels}
    for el in tree:
        t = str(getattr(el, "text", "")).strip().lower()
        if t in wanted and getattr(el, "bounds", None):
            return el
    return None


def _tap_el(driver, el) -> None:
    b = el.bounds
    driver.click((b.left + b.right) // 2, (b.top + b.bottom) // 2)


def google_login_shell(session_id: str, email: str, password: str) -> Dict[str, Any]:
    """
    Best-effort agent-assisted sign-in. Fills email + password, then stops at
    Google's 2FA wall (which the human must clear). Returns:
        {"success": bool, "account": str | None, "error": str | None}
    error == "2fa_required"  → ask the owner to approve on their phone, or run
                               scripts/login.sh.
    """
    driver = SessionManager.get_driver(session_id)
    adb_client = SessionManager.get_adb_client(session_id)
    if not driver or not adb_client:
        return {"success": False, "account": None, "error": "No driver/ADB client"}

    if SessionManager.is_simulated(session_id):
        return {"success": True, "account": email, "error": None}

    serial = getattr(driver, "serial", None) or "emulator-5554"

    try:
        # Launch Play Store fresh
        adb_client.force_stop("com.android.vending")
        time.sleep(1)
        adb_client.run_cmd(["shell", "am", "start", "-n",
                            "com.android.vending/.AssetBrowserActivity"])
        time.sleep(3)

        # Tap "Sign in" if present
        tree = driver.get_tree()
        signin = _find_text(tree, "Sign in")
        if signin:
            _tap_el(driver, signin)
            time.sleep(4)

        # Work through up to ~10 screens until both fields are filled & submitted.
        email_done = False
        password_done = False
        for _ in range(10):
            tree = driver.get_tree()

            # Dismiss the common interstitials first.
            skip = _find_text(tree, "Skip", "Close", "No thanks", "Not now")
            edit = _find_editable(tree)
            # Only skip if there's no editable field to fill on this screen,
            # so we don't skip past the email/password entry.
            if skip and not edit:
                _tap_el(driver, skip)
                time.sleep(2)
                continue

            curr = ""
            try:
                curr = driver.app_current().get("package", "")
            except Exception:
                pass

            # Detect the 2FA / "verify it's you" wall — unpassable by automation.
            if _find_text(tree, "Verify it's you", "Check your", "2-Step Verification"):
                return {"success": False, "account": None, "error": "2fa_required"}

            if edit and not email_done:
                _tap_el(driver, edit)
                time.sleep(1.5)
                _adb_input_text(serial, email)
                time.sleep(1)
                nxt = _find_text(tree, "Next") or _find_text(driver.get_tree(), "Next")
                if nxt:
                    _tap_el(driver, nxt)
                email_done = True
                time.sleep(4)
                continue

            if edit and email_done and not password_done:
                _tap_el(driver, edit)
                time.sleep(1.5)
                _adb_input_text(serial, password)
                time.sleep(1)
                nxt = _find_text(driver.get_tree(), "Next")
                if nxt:
                    _tap_el(driver, nxt)
                password_done = True
                time.sleep(5)
                continue

            # Post-auth "I agree" / "Accept" screens
            agree = _find_text(tree, "I agree", "Agree", "Accept", "More", "Got it")
            if agree:
                _tap_el(driver, agree)
                time.sleep(2)
                continue

            # Reached a search-bar / home state?
            if any("search" in str(getattr(el, "text", "")).lower()
                   for el in tree):
                break

        # Confirm
        acc = get_playstore_account(session_id)
        if acc.get("signed_in"):
            return {"success": True, "account": acc.get("account", email), "error": None}

        if password_done:
            # Filled creds but couldn't confirm — almost always the 2FA wall.
            return {"success": False, "account": None, "error": "2fa_required"}
        return {"success": False, "account": None,
                "error": "Could not complete sign-in via automation; use scripts/login.sh"}

    except Exception as e:
        logger.exception("google_login_shell error")
        return {"success": False, "account": None, "error": str(e)}
