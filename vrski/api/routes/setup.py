from fastapi import APIRouter, Query
from pydantic import BaseModel
from vrski.credentials import save_credentials, has_credentials, get_email, load_credentials
from vrski.session.manager import SessionManager
from vrski.playstore.auth import get_playstore_account, signin_playstore

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    session_id: str
    email: str
    password: str


@router.post("")
def run_setup(req: SetupRequest):
    """
    Saves Google credentials to .env and signs the device into Play Store.

    Designed for agent first-run onboarding: agent asks owner for credentials
    once, calls this endpoint, and all future sessions are pre-authenticated.
    """
    # 1. Persist credentials
    save_credentials(req.email, req.password)

    # 2. Check if already signed in with this account
    account_info = get_playstore_account(req.session_id)
    if account_info.get("signed_in") and account_info.get("account") == req.email:
        return {
            "success": True,
            "account": req.email,
            "already_signed_in": True,
            "message": "Credentials saved. Device already signed in with this account.",
        }

    # 3. Perform sign-in
    result = signin_playstore(req.session_id, req.email, req.password)
    if result.get("success"):
        return {
            "success": True,
            "account": result.get("account", req.email),
            "already_signed_in": False,
            "message": "Credentials saved and signed in to Play Store successfully.",
        }

    # 4. 2FA wall — only the owner's phone can clear it
    if result.get("error") == "2fa_required":
        return {
            "success": False,
            "account": req.email,
            "credentials_saved": True,
            "error": "2fa_required",
            "message": (
                "Email and password were entered, but Google is asking to verify "
                "it's you. Approve the prompt on your phone, OR run "
                "`bash scripts/login.sh` to finish the sign-in by hand."
            ),
        }

    # 5. Credentials saved even if sign-in failed (device may not be running yet)
    return {
        "success": False,
        "account": req.email,
        "credentials_saved": True,
        "error": result.get("error", "Sign-in failed"),
        "message": (
            "Credentials saved. Automated sign-in could not complete — "
            "run `bash scripts/login.sh` to sign in by hand (recommended)."
        ),
    }


@router.get("/status")
def check_setup_status(session_id: str = Query(...)):
    """
    Returns setup readiness for the given session.

    Agents call this at the start of every session. If ready=false and
    has_credentials=false, the agent should ask the owner for their Google
    email and password, then call POST /setup.
    """
    saved = has_credentials()
    email = get_email()

    # Check live sign-in state on the device if a session is active
    signed_in = False
    active_account = None
    driver_available = SessionManager.get_driver(session_id) is not None

    if driver_available:
        account_info = get_playstore_account(session_id)
        signed_in = account_info.get("signed_in", False)
        active_account = account_info.get("account")

    ready = saved and (signed_in or not driver_available)

    return {
        "ready": ready,
        "has_credentials": saved,
        "saved_email": email,
        "signed_in": signed_in,
        "active_account": active_account,
        "driver_available": driver_available,
        "next_step": (
            None if ready
            else "call vrski_setup(session_id, email, password) with owner's Google credentials"
            if not saved
            else "call vrski_signin_playstore(session_id) to authenticate with saved credentials"
        ),
    }
