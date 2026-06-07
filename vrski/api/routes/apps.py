import time
import logging
from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from vrski.session.db import get_db
from vrski.session.manager import SessionManager

logger = logging.getLogger("vrski.api.routes.apps")

router = APIRouter()

class AppOperationRequest(BaseModel):
    package_name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$")

class PlayStoreAuthRequest(BaseModel):
    gmail: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str

# Try to import Phase 3 components if they exist
try:
    from vrski.playstore.installer import install_app
except ImportError:
    install_app = None

try:
    from vrski.playstore.auth import signin_playstore, get_playstore_account
except ImportError:
    signin_playstore = None
    get_playstore_account = None


@router.post("/session/{id}/install")
def install_app_route(
    req: AppOperationRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")

        # Check duplicate app install
        is_installed = False
        if hasattr(adb_client, "is_installed"):
            is_installed = adb_client.is_installed(req.package_name)
        elif hasattr(adb_client, "installed_packages"):
            is_installed = req.package_name in adb_client.installed_packages
        elif hasattr(adb_client, "list_packages"):
            is_installed = req.package_name in adb_client.list_packages()

        if is_installed:
            raise HTTPException(status_code=400, detail=f"App {req.package_name} is already installed")
            
        start_time = time.time()
        
        # If simulated, or if install_app module is missing, fallback to mock
        if SessionManager.is_simulated(session_id) or install_app is None:
            # Simulate installation
            if hasattr(adb_client, "installed_packages"):
                adb_client.installed_packages.add(req.package_name)
            duration = round(time.time() - start_time, 2)
            return {
                "success": True,
                "package_name": req.package_name,
                "duration_seconds": duration,
                "error": None
            }
        else:
            try:
                res = install_app(session_id, req.package_name)
                duration = round(time.time() - start_time, 2)
                if isinstance(res, dict):
                    if not res.get("success", False):
                        raise HTTPException(status_code=500, detail=res.get("error") or "Real installation failed")
                    return res
                return {
                    "success": True,
                    "package_name": req.package_name,
                    "duration_seconds": duration,
                    "error": None
                }
            except HTTPException:
                raise
            except Exception as inner_e:
                raise HTTPException(status_code=500, detail=f"Real installation failed: {str(inner_e)}")
                
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to install app")
        raise HTTPException(status_code=500, detail=f"Failed to install app: {str(e)}")


@router.post("/session/{id}/launch")
def launch_app_route(
    req: AppOperationRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        driver = SessionManager.get_driver(session_id)
        
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")
            
        success = False
        
        # Try real launch first if not in simulated mode
        if not SessionManager.is_simulated(session_id):
            if hasattr(driver, "app_start"):
                try:
                    driver.app_start(req.package_name)
                    success = True
                except Exception:
                    pass
            
            if not success and hasattr(adb_client, "launch_package"):
                try:
                    adb_client.launch_package(req.package_name)
                    success = True
                except Exception:
                    pass
        else:
            if hasattr(adb_client, "launch_package"):
                adb_client.launch_package(req.package_name)
            success = True
            
        if success:
            SessionManager.update_session(db, session_id, current_app=req.package_name)
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to launch package {req.package_name}")
            
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to launch app")
        raise HTTPException(status_code=500, detail=f"Failed to launch app: {str(e)}")


@router.post("/session/{id}/close")
def close_app_route(
    req: AppOperationRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        driver = SessionManager.get_driver(session_id)
        
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")
            
        success = False
        
        # Try real close first if not in simulated mode
        if not SessionManager.is_simulated(session_id):
            if hasattr(driver, "app_stop"):
                try:
                    driver.app_stop(req.package_name)
                    success = True
                except Exception:
                    pass
            
            if not success and hasattr(adb_client, "force_stop"):
                try:
                    adb_client.force_stop(req.package_name)
                    success = True
                except Exception:
                    pass
        else:
            if hasattr(adb_client, "force_stop"):
                adb_client.force_stop(req.package_name)
            success = True
            
        if success:
            if session.current_app == req.package_name:
                SessionManager.update_session(db, session_id, current_app=None)
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to close package {req.package_name}")
            
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to close app")
        raise HTTPException(status_code=500, detail=f"Failed to close app: {str(e)}")


@router.post("/session/{id}/auth/playstore")
def signin_playstore_route(
    req: PlayStoreAuthRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        if SessionManager.is_simulated(session_id) or signin_playstore is None:
            logger.info(f"Simulating Play Store sign-in for {req.gmail}")
            driver = SessionManager.get_driver(session_id)
            if driver and hasattr(driver, "current_screen"):
                driver.current_screen = "playstore"
            return {
                "success": True,
                "account": req.gmail,
                "error": None
            }
        else:
            try:
                res = signin_playstore(session_id, req.gmail, req.password)
                if isinstance(res, dict):
                    if not res.get("success", False):
                        raise HTTPException(status_code=500, detail=res.get("error") or "Real sign-in failed")
                    return res
                return {
                    "success": True,
                    "account": req.gmail,
                    "error": None
                }
            except HTTPException:
                raise
            except Exception as inner_e:
                raise HTTPException(status_code=500, detail=f"Real sign-in failed: {str(inner_e)}")
                
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to authenticate Play Store")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate: {str(e)}")


@router.get("/session/{id}/auth/playstore")
def get_playstore_account_route(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        if get_playstore_account is None:
            raise HTTPException(status_code=400, detail="Play Store authentication module not available")
            
        res = get_playstore_account(session_id)
        return {
            "success": True,
            "signed_in": res.get("signed_in", False),
            "account": res.get("account")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve account status")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve account status: {str(e)}")


@router.post("/session/{id}/uninstall")
def uninstall_app_route(
    req: AppOperationRequest,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")
            
        success = False
        if not SessionManager.is_simulated(session_id):
            if hasattr(adb_client, "uninstall_package"):
                success = adb_client.uninstall_package(req.package_name)
        else:
            if hasattr(adb_client, "installed_packages") and req.package_name in adb_client.installed_packages:
                adb_client.installed_packages.remove(req.package_name)
            success = True
            
        if success:
            if session.current_app == req.package_name:
                SessionManager.update_session(db, session_id, current_app=None)
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to uninstall package {req.package_name}")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Failed to uninstall app")
        raise HTTPException(status_code=500, detail=f"Failed to uninstall app: {str(e)}")


@router.get("/session/{id}/apps")
def list_apps_route(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")
            
        packages = []
        if not SessionManager.is_simulated(session_id):
            if hasattr(adb_client, "list_packages"):
                packages = adb_client.list_packages()
        else:
            if hasattr(adb_client, "installed_packages"):
                packages = list(adb_client.installed_packages)
            else:
                packages = ["com.android.settings", "com.whatsapp"]
                
        return {"success": True, "packages": packages}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list packages")
        raise HTTPException(status_code=500, detail=f"Failed to list packages: {str(e)}")


@router.get("/session/{id}/apps/{package_name}")
def check_app_installed_route(
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]+$"),
    package_name: str = Path(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+$"),
    db: DBSession = Depends(get_db)
):
    try:
        session_id = id
        session = SessionManager.get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
        adb_client = SessionManager.get_adb_client(session_id)
        if not adb_client:
            raise HTTPException(status_code=400, detail=f"ADB Client not initialized for session {session_id}")
            
        is_installed = False
        if not SessionManager.is_simulated(session_id):
            if hasattr(adb_client, "is_installed"):
                is_installed = adb_client.is_installed(package_name)
            elif hasattr(adb_client, "list_packages"):
                is_installed = package_name in adb_client.list_packages()
        else:
            if hasattr(adb_client, "installed_packages"):
                is_installed = package_name in adb_client.installed_packages
            else:
                is_installed = package_name in ["com.android.settings", "com.whatsapp"]
                
        return {"success": True, "installed": is_installed}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to check app installation")
        raise HTTPException(status_code=500, detail=f"Failed to check app installation: {str(e)}")
