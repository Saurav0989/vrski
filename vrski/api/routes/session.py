from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from vrski.session.db import get_db
from vrski.session.manager import SessionManager

router = APIRouter(prefix="/session")

class StartSessionRequest(BaseModel):
    session_id: str

@router.post("/start")
def start_session(req: StartSessionRequest, db: DBSession = Depends(get_db)):
    try:
        # If the session row already exists, re-attach a live driver if its
        # in-memory drivers were lost (e.g. the API restarted) instead of erroring.
        existing = SessionManager.get_session(db, req.session_id)
        if existing:
            reattached = SessionManager.get_driver(req.session_id) is None
            if reattached:
                SessionManager.reattach_session(req.session_id, existing.emulator_serial)
            return {
                "success": True,
                "session_id": existing.id,
                "status": existing.status,
                "emulator_serial": existing.emulator_serial,
                "reattached": reattached,
            }

        session = SessionManager.start_session(db, req.session_id)
        return {
            "success": True,
            "session_id": session.id,
            "status": session.status,
            "emulator_serial": session.emulator_serial
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@router.post("/{id}/end")
def end_session(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.end_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {
            "success": True,
            "status": "ended"
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")

@router.get("/{id}/status")
def get_session_status(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Try to resolve app and activity
        current_app = session.current_app
        current_activity = None

        driver = SessionManager.get_driver(session_id)
        adb_client = SessionManager.get_adb_client(session_id)

        if driver and hasattr(driver, "app_current"):
            try:
                curr = driver.app_current()
                if curr.get("package"): current_app = curr["package"]
                if curr.get("activity"): current_activity = curr["activity"]
            except Exception:
                pass
        elif adb_client:
            if hasattr(adb_client, "running_package"):
                current_app = adb_client.running_package
            elif hasattr(adb_client, "get_current_package_and_activity"):
                try:
                    current_app, current_activity = adb_client.get_current_package_and_activity()
                except Exception:
                    pass
                    
        return {
            "success": True,
            "session_id": session.id,
            "status": session.status,
            "current_app": current_app,
            "current_activity": current_activity
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")
