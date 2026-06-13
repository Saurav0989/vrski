import time
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session as DBSession
from vrski.session.db import get_db
from vrski.session.manager import SessionManager

logger = logging.getLogger("vrski.api.routes.screen")

router = APIRouter()

MOCK_SCREENSHOT_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

def serialize_element(el) -> dict:
    if isinstance(el, dict):
        return {
            "id": el.get("id") or el.get("element_id") or "",
            "type": el.get("type") or el.get("element_type") or "",
            "text": el.get("text") or "",
            "content_desc": el.get("content_desc") or "",
            "clickable": bool(el.get("clickable")),
            "scrollable": bool(el.get("scrollable")),
            "editable": bool(el.get("editable")),
            "bounds": el.get("bounds") or {}
        }
        
    bounds_val = getattr(el, "bounds", None)
    bounds_dict = {}
    if bounds_val:
        if isinstance(bounds_val, dict):
            bounds_dict = bounds_val
        else:
            bounds_dict = {
                "left": getattr(bounds_val, "left", 0),
                "top": getattr(bounds_val, "top", 0),
                "right": getattr(bounds_val, "right", 0),
                "bottom": getattr(bounds_val, "bottom", 0)
            }
            
    return {
        "id": getattr(el, "element_id", getattr(el, "id", "")),
        "type": getattr(el, "element_type", getattr(el, "type", "")),
        "text": getattr(el, "text", ""),
        "content_desc": getattr(el, "content_desc", ""),
        "clickable": bool(getattr(el, "clickable", False)),
        "scrollable": bool(getattr(el, "scrollable", False)),
        "editable": bool(getattr(el, "editable", False)),
        "bounds": bounds_dict
    }

# Resource-id markers for pure chrome that floods the tree without being a task
# target: the system status bar, soft-keyboard keys, and system bar backgrounds.
_NOISE_ID_MARKERS = (
    "com.android.systemui",
    "key_pos",
    "inputmethod",
    "navigationBarBackground",
    "statusBarBackground",
)


def _is_salient(el: dict) -> bool:
    """True if an element is worth showing an agent by default.

    Drops textless, non-interactive layout containers (the empty FrameLayout/
    LinearLayout/View wrappers that make up most of a raw dump), the system status
    bar, and soft-keyboard keys. Anything carrying text or a content description,
    or that is clickable/scrollable/editable, is kept.
    """
    idn = el.get("id") or ""
    if any(marker in idn for marker in _NOISE_ID_MARKERS):
        return False
    return bool(
        el.get("text")
        or el.get("content_desc")
        or el.get("clickable")
        or el.get("scrollable")
        or el.get("editable")
    )


@router.get("/session/{id}/screen")
def get_screen(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    include_screenshot: bool = False,
    salient: bool = True,
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        driver = SessionManager.get_driver(session_id)
        adb_client = SessionManager.get_adb_client(session_id)
        
        if not driver:
            raise HTTPException(status_code=400, detail=f"Driver not initialized for session {session_id}")
            
        raw_elements = driver.get_tree()
        elements = [serialize_element(el) for el in raw_elements]
        raw_element_count = len(elements)
        # By default return only agent-relevant elements; raw tree via salient=false.
        if salient:
            elements = [el for el in elements if _is_salient(el)]

        package = "unknown"
        activity = "unknown"

        # Try real driver first (most reliable source for package/activity)
        if driver and hasattr(driver, "app_current"):
            try:
                curr = driver.app_current()
                if curr.get("package"): package = curr["package"]
                if curr.get("activity"): activity = curr["activity"]
            except Exception:
                pass

        # Fallback for mock driver which has running_package
        if package == "unknown" and adb_client:
            if hasattr(adb_client, "running_package"):
                package = adb_client.running_package
            elif hasattr(adb_client, "get_current_package_and_activity"):
                try:
                    p, a = adb_client.get_current_package_and_activity()
                    if p: package = p
                    if a: activity = a
                except Exception:
                    pass
                    
        # Update current app dynamically if it has changed
        if package != "unknown" and package != session.current_app:
            try:
                SessionManager.update_session(db, session_id, current_app=package)
            except Exception as db_e:
                logger.error(f"Failed to update current app in DB: {db_e}")
                db.rollback()

        screenshot_base64 = None
        if include_screenshot:
            if SessionManager.is_simulated(session_id):
                screenshot_base64 = MOCK_SCREENSHOT_BASE64
            else:
                try:
                    if hasattr(driver, "get_screenshot_base64"):
                        screenshot_base64 = driver.get_screenshot_base64()
                    elif hasattr(adb_client, "take_screenshot_base64"):
                        screenshot_base64 = adb_client.take_screenshot_base64()
                except Exception as e:
                    logger.warning(f"Failed to capture screenshot: {e}")
                    screenshot_base64 = None
                    
        return {
            "success": True,
            "elements": elements,
            "element_count": len(elements),
            "raw_element_count": raw_element_count,
            "salient": salient,
            "package": package,
            "activity": activity,
            "screenshot_base64": screenshot_base64
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get screen tree")
        raise HTTPException(status_code=500, detail=f"Failed to get screen tree: {str(e)}")


class WaitRequest(BaseModel):
    text: Optional[str] = None
    element_id: Optional[str] = None
    timeout: int = Field(15, gt=0, le=120)

    @model_validator(mode="after")
    def verify_targets(self) -> 'WaitRequest':
        if not self.text and not self.element_id:
            raise ValueError("At least one of 'text' or 'element_id' must be specified.")
        return self


@router.post("/session/{id}/wait")
async def wait_for_element_route(
    req: WaitRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        driver = SessionManager.get_driver(session_id)
        if not driver:
            raise HTTPException(status_code=400, detail=f"Driver not initialized for session {session_id}")
            
        start_time = time.time()
        found = False
        matched_el = None
        
        while time.time() - start_time < req.timeout:
            # Wrap blocking get_tree Call to prevent blocking the event loop thread
            raw_elements = await asyncio.to_thread(driver.get_tree)
            for el in raw_elements:
                el_text = getattr(el, "text", "")
                el_id = getattr(el, "element_id", getattr(el, "id", ""))
                
                if req.text and el_text == req.text:
                    found = True
                    matched_el = el
                    break
                if req.element_id and el_id == req.element_id:
                    found = True
                    matched_el = el
                    break
                    
            if found:
                break
            await asyncio.sleep(1.0)
            
        if found and matched_el:
            return {
                "success": True,
                "found": True,
                "element": serialize_element(matched_el)
            }
        else:
            return {
                "success": True,
                "found": False,
                "element": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed waiting for element")
        raise HTTPException(status_code=500, detail=f"Failed waiting for element: {str(e)}")
