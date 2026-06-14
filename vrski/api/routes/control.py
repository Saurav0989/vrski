"""Phase 3 — trust/control/audit endpoints: policy, approval, audit, kill-switch."""
import logging
from dataclasses import asdict
from typing import Optional, List
from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from vrski.session.db import get_db
from vrski.session.manager import SessionManager
from vrski.control import ControlManager
from vrski.api.routes.actions import do_semantic_tap

logger = logging.getLogger("vrski.api.routes.control")
router = APIRouter()


class PolicyRequest(BaseModel):
    require_approval_for_sensitive: Optional[bool] = None
    dry_run: Optional[bool] = None
    blocked_labels: Optional[List[str]] = None
    max_sensitive_actions: Optional[int] = None


class ApproveRequest(BaseModel):
    pending_id: str
    approved: bool = True


def _require_session(db: DBSession, session_id: str):
    session = SessionManager.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@router.post("/session/{id}/policy")
def set_policy(req: PolicyRequest, id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), db: DBSession = Depends(get_db)):
    _require_session(db, id)
    p = ControlManager.set_policy(id, **req.model_dump(exclude_none=True))
    return {"success": True, "policy": asdict(p)}


@router.get("/session/{id}/policy")
def get_policy(id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), db: DBSession = Depends(get_db)):
    _require_session(db, id)
    st = ControlManager.get(id)
    return {
        "success": True,
        "policy": asdict(st.policy),
        "paused": st.paused,
        "sensitive_count": st.sensitive_count,
        "pending": [{"pending_id": k, **v.get("meta", {})} for k, v in st.pending.items()],
    }


@router.post("/session/{id}/pause")
def pause(id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), db: DBSession = Depends(get_db)):
    _require_session(db, id)
    ControlManager.set_paused(id, True)
    return {"success": True, "paused": True}


@router.post("/session/{id}/resume")
def resume(id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), db: DBSession = Depends(get_db)):
    _require_session(db, id)
    ControlManager.set_paused(id, False)
    return {"success": True, "paused": False}


@router.get("/session/{id}/audit")
def get_audit(id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), limit: int = 200, db: DBSession = Depends(get_db)):
    _require_session(db, id)
    return {"success": True, "entries": ControlManager.read_audit(id, limit=limit)}


@router.post("/session/{id}/approve")
def approve(req: ApproveRequest, id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"), db: DBSession = Depends(get_db)):
    """Execute (or discard) a pending sensitive action — the owner's explicit yes/no."""
    _require_session(db, id)
    pending = ControlManager.pop_pending(id, req.pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail=f"No pending approval '{req.pending_id}' (already resolved or expired)")

    meta = pending.get("meta", {})
    if not req.approved:
        ControlManager.audit(id, {"kind": "approval_denied", "pending_id": req.pending_id, "what": meta.get("what")})
        return {"success": True, "approved": False, "executed": False, "what": meta.get("what")}

    # The kill-switch overrides even an approval.
    if ControlManager.get(id).paused:
        raise HTTPException(status_code=409, detail="Session is paused; resume before approving actions.")

    driver = SessionManager.get_driver(id)
    if not driver:
        raise HTTPException(status_code=400, detail=f"Driver not initialized for session {id}")

    ControlManager.audit(id, {"kind": "approval_granted", "pending_id": req.pending_id, "what": meta.get("what")})
    a = pending["action"]
    result = do_semantic_tap(driver, id, a.get("text"), a.get("element_id"), a.get("content_desc"), bypass_gate=True)
    return {"success": True, "approved": True, "executed": True, "what": meta.get("what"), "result": result}
