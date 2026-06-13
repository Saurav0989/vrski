import logging
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlmodel import Session as DBSession
from vrski.session.db import get_db
from vrski.session.manager import SessionManager

logger = logging.getLogger("vrski.api.routes.actions")

router = APIRouter()


def _capture_screenshot(driver) -> Optional[str]:
    """Returns a base64 screenshot or None on failure — never raises."""
    try:
        if hasattr(driver, "get_screenshot_base64"):
            return driver.get_screenshot_base64()
    except Exception as e:
        logger.warning(f"Could not capture screenshot: {e}")
    return None

class ActionRequest(BaseModel):
    type: Literal["tap", "type", "swipe", "scroll_to", "back", "home", "recent_apps"]
    
    # Tap / Scroll target parameters
    text: Optional[str] = None
    element_id: Optional[str] = None
    content_desc: Optional[str] = None
    x: Optional[int] = Field(None, ge=0)
    y: Optional[int] = Field(None, ge=0)
    
    # Type parameters
    clear_first: Optional[bool] = True
    
    # Swipe parameters
    direction: Optional[Literal["up", "down", "left", "right"]] = None
    distance: Optional[int] = Field(500, gt=0)
    speed: Optional[int] = Field(300, gt=0)

    @model_validator(mode="after")
    def validate_action_fields(self) -> 'ActionRequest':
        if self.type == "tap":
            has_coords = self.x is not None or self.y is not None
            has_semantic = self.text is not None or self.element_id is not None or self.content_desc is not None
            
            if not has_coords and not has_semantic:
                raise ValueError("For tap action, either coordinates (x, y) or at least one identifier (text, element_id, content_desc) must be provided")
            
            if has_coords:
                if self.x is None or self.y is None:
                    raise ValueError("For coordinate tap, both x and y must be provided")
                
        elif self.type == "type":
            if self.text is None:
                raise ValueError("text is required for type action")
                
        elif self.type == "swipe":
            if self.direction is None:
                raise ValueError("direction is required for swipe action")
                
        elif self.type == "scroll_to":
            if self.text is None:
                raise ValueError("text is required for scroll_to action")
                
        return self

def _el_fields(el):
    """Extracts (text, id, content_desc, clickable, editable) from a dict or UIElement."""
    if isinstance(el, dict):
        return (
            el.get("text") or "",
            el.get("id") or el.get("element_id") or "",
            el.get("content_desc") or "",
            bool(el.get("clickable")),
            bool(el.get("editable")),
        )
    return (
        getattr(el, "text", "") or "",
        getattr(el, "element_id", getattr(el, "id", "")) or "",
        getattr(el, "content_desc", "") or "",
        bool(getattr(el, "clickable", False)),
        bool(getattr(el, "editable", False)),
    )


def find_tap_candidates(tree: list, text: Optional[str] = None, element_id: Optional[str] = None, content_desc: Optional[str] = None) -> list:
    """Returns every element matching any provided identifier (exact match)."""
    candidates = []
    for el in tree:
        el_text, el_id, el_desc, _, _ = _el_fields(el)
        if text is not None and el_text == text:
            candidates.append(el)
        elif element_id is not None and el_id == element_id:
            candidates.append(el)
        elif content_desc is not None and el_desc == content_desc:
            candidates.append(el)
    return candidates


def _tap_rank(el) -> int:
    """Higher = better tap target when several elements share the same label.

    Prefer a labelled/actionable target over the text field that merely *contains*
    the same string (e.g. a search box echoing the typed query). max() is stable,
    so ties keep original tree order.
    """
    _t, _i, _d, clickable, editable = _el_fields(el)
    score = 0
    if not editable:
        score += 4   # a button / list row beats the input field holding the same text
    if clickable:
        score += 2
    return score

@router.post("/session/{id}/action")
def execute_action(
    action: ActionRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
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
            
        if action.type == "tap":
            # 1. Coordinate tap
            if action.x is not None and action.y is not None:
                if hasattr(driver, "tap_coordinates"):
                    driver.tap_coordinates(action.x, action.y)
                elif hasattr(driver, "click"):
                    driver.click(action.x, action.y)
                elif hasattr(driver, "tap"):
                    try:
                        driver.tap(action.x, action.y)
                    except TypeError:
                        driver.tap({"bounds": {"left": action.x, "top": action.y, "right": action.x, "bottom": action.y}})
                else:
                    raise HTTPException(status_code=400, detail="Driver does not support coordinate taps")
                return {"success": True, "matched_element": None}

            # 2. Semantic element tap — gather all matches, then pick the best target.
            tree = driver.get_tree()
            candidates = find_tap_candidates(tree, action.text, action.element_id, action.content_desc)
            if not candidates:
                screenshot_b64 = _capture_screenshot(driver)
                return {
                    "success": False,
                    "matched_element": None,
                    "matched_count": 0,
                    "error": f"Element not found: text={action.text}, id={action.element_id}, desc={action.content_desc}",
                    "screenshot_base64": screenshot_b64,
                }

            # When several elements share the same label, prefer the actionable
            # target over an input field that merely echoes the text.
            matched = max(candidates, key=_tap_rank)
            res = driver.tap(matched)
            matched_id = matched.get("id") if isinstance(matched, dict) else getattr(matched, "element_id", getattr(matched, "id", None))
            result = {
                "success": res.get("success", True) if isinstance(res, dict) else True,
                "matched_element": matched_id,
                "matched_count": len(candidates),
            }
            if len(candidates) > 1:
                result["ambiguous"] = True
            return result
            
        elif action.type == "type":
            if action.text is None:
                raise HTTPException(status_code=400, detail="text is required for type action")
            res = driver.type_text(action.text, clear_first=action.clear_first)
            success = res.get("success", True) if isinstance(res, dict) else bool(res)
            if not success:
                return {
                    "success": False,
                    "error": "No focused input field to type into. Tap a text field first, then type.",
                    "screenshot_base64": _capture_screenshot(driver),
                }
            return {"success": True}
            
        elif action.type == "swipe":
            if action.direction is None:
                raise HTTPException(status_code=400, detail="direction is required for swipe action")
            res = driver.swipe(action.direction, distance=action.distance, speed=action.speed)
            return {
                "success": res.get("success", True) if isinstance(res, dict) else True
            }
            
        elif action.type == "scroll_to":
            if action.text is None:
                raise HTTPException(status_code=400, detail="text is required for scroll_to action")
            res = driver.scroll_to(action.text)
            return {
                "success": res.get("success", True) if isinstance(res, dict) else True,
                "found": res.get("found", True) if isinstance(res, dict) else True
            }
            
        elif action.type == "back":
            if adb_client and hasattr(adb_client, "key_back"):
                adb_client.key_back()
            elif hasattr(driver, "press"):
                driver.press("back")
            else:
                raise HTTPException(status_code=400, detail="Back action not supported by driver or adb client")
            return {"success": True}
            
        elif action.type == "home":
            if adb_client and hasattr(adb_client, "key_home"):
                adb_client.key_home()
            elif hasattr(driver, "press"):
                driver.press("home")
            else:
                raise HTTPException(status_code=400, detail="Home action not supported by driver or adb client")
            return {"success": True}
            
        elif action.type == "recent_apps":
            if adb_client and hasattr(adb_client, "key_recent_apps"):
                adb_client.key_recent_apps()
            elif hasattr(driver, "press"):
                driver.press("recent")
            else:
                raise HTTPException(status_code=400, detail="Recent apps action not supported by driver or adb client")
            return {"success": True}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {action.type}")
            
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error executing action")
        raise HTTPException(status_code=500, detail=f"Failed to execute action: {str(e)}")
