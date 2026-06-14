"""Login / verification "wall" detection.

Classifies the current screen as a wall the agent must handle — and crucially,
whether it's a HUMAN-ONLY wall (CAPTCHA / anti-bot block, OTP, 2-Step) that the
agent must hand back to the owner rather than try to defeat. Also detects login
screens and whether they offer an SSO method the agent CAN complete with the
device's existing Google account.

Discovered live driving Grubhub: install + launch + "Continue with Google" all
work, but the app's PerimeterX anti-bot check then blocks the session. The UI
layer is rarely the blocker for commercial apps — anti-bot detection is.
"""
from typing import List, Dict, Any

# Anti-bot / CAPTCHA vendors and phrasings — human-only, often unsolvable by automation.
_BOT_SIGNS = (
    "not a robot", "request blocked", "hit a roadblock", "roadblock",
    "captcha", "recaptcha", "hcaptcha", "datadome", "perimeterx",
    "press & hold", "press and hold", "verify you are human", "are you a human",
    "unusual traffic",
)
_BOT_ACTIVITY = ("perimeterx", "pxblock", "captcha", "datadome", "recaptcha")

# One-time codes / phone or email verification — the code goes to the owner.
_OTP_SIGNS = (
    "one-time", "one time code", "verification code", "enter the code",
    "enter code", "we sent a code", "sent you a code", "6-digit", "4-digit",
    "otp", "sms code", "confirm your number", "code we sent",
)

# Google "verify it's you" / 2-step — only the owner's phone can clear it.
_2FA_SIGNS = ("verify it's you", "verify its you", "2-step verification", "two-factor")

# Login / sign-in entry points.
_LOGIN_SIGNS = ("sign in", "log in", "login", "sign up", "create an account", "continue with")

# SSO the AGENT can complete using the device's existing account.
_SSO_GOOGLE = ("continue with google", "sign in with google")


def _texts(elements: List[Any]) -> List[str]:
    out = []
    for e in elements:
        if isinstance(e, dict):
            t, d = (e.get("text") or "").strip(), (e.get("content_desc") or "").strip()
        else:
            t = (getattr(e, "text", "") or "").strip()
            d = (getattr(e, "content_desc", "") or "").strip()
        if t:
            out.append(t)
        if d:
            out.append(d)
    return out


def classify_wall(elements: List[Any], activity: str = "", package: str = "") -> Dict[str, Any]:
    """Return {wall, human_required, reason, message, ...} for the current screen."""
    texts = _texts(elements)
    blob = " || ".join(texts).lower()
    act = (activity or "").lower()

    # 1. Anti-bot / CAPTCHA block.
    if any(s in act for s in _BOT_ACTIVITY) or any(s in blob for s in _BOT_SIGNS):
        return {
            "wall": "bot_block",
            "human_required": True,
            "reason": "An anti-bot / CAPTCHA check (e.g. PerimeterX) is blocking the session.",
            "message": ("This app detected automation and is showing a 'prove you're not a robot' "
                        "challenge. An agent cannot and should not solve it — hand back to the "
                        "owner, or this app needs a real (non-emulator) device."),
        }

    # 2. One-time code / phone-or-email verification.
    if any(s in blob for s in _OTP_SIGNS):
        return {
            "wall": "otp",
            "human_required": True,
            "reason": "A one-time verification code is required.",
            "message": "Ask the owner for the code sent to their phone/email; do not guess it.",
        }

    # 3. Google 2-Step / "verify it's you".
    if any(s in blob for s in _2FA_SIGNS):
        return {
            "wall": "2fa",
            "human_required": True,
            "reason": "Google 2-Step Verification.",
            "message": "Only the owner's phone can approve this. Hand back to the owner.",
        }

    # 4. Login screen — list methods; Google SSO is agent-completable.
    if any(s in blob for s in _LOGIN_SIGNS):
        google_sso = any(s in blob for s in _SSO_GOOGLE)
        methods = [t for t in texts if t.lower().startswith("continue with") or t.lower() in ("sign in", "log in", "sign up")]
        return {
            "wall": "login",
            "human_required": not google_sso,
            "reason": "A login / sign-in screen.",
            "google_sso_available": google_sso,
            "methods": methods,
            "message": ("Use 'Continue with Google' — the agent can complete it with the device's "
                        "existing account (no password, no code)." if google_sso else
                        "No agent-completable SSO offered (email/phone/OTP); likely needs the owner."),
        }

    return {"wall": "none", "human_required": False, "reason": "", "message": ""}
