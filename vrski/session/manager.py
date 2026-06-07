import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import Session as DBSession, select
from vrski.session.models import Session

logger = logging.getLogger("vrski.session.manager")

# In-memory mapping of session_id to driver and adb client
_active_drivers: Dict[str, Any] = {}
_active_adb_clients: Dict[str, Any] = {}
_simulated_sessions: Dict[str, bool] = {}

# Try to import real modules if they exist (Phase 1 components)
try:
    from vrski.ui.driver import UIDriver
except ImportError:
    UIDriver = None

try:
    from vrski.adb.client import ADBClient
except ImportError:
    ADBClient = None


class MockADBClient:
    def __init__(self, serial: str):
        self.serial = serial
        self.installed_packages = {"com.android.settings", "com.android.vending"}
        self.running_package = "com.android.settings"

    def install_apk(self, path: str) -> bool:
        logger.info(f"[Mock ADB] Installing APK from {path}")
        self.installed_packages.add("com.instagram.android")
        return True

    def uninstall_package(self, package: str) -> bool:
        logger.info(f"[Mock ADB] Uninstalling package {package}")
        self.installed_packages.discard(package)
        return True

    def launch_package(self, package: str) -> bool:
        logger.info(f"[Mock ADB] Launching package {package}")
        self.running_package = package
        return True

    def force_stop(self, package: str) -> bool:
        logger.info(f"[Mock ADB] Force stopping package {package}")
        if self.running_package == package:
            self.running_package = "com.android.launcher3"
        return True

    def list_packages(self) -> list[str]:
        return list(self.installed_packages)

    def key_back(self) -> bool:
        logger.info("[Mock ADB] Key event: BACK")
        return True

    def key_home(self) -> bool:
        logger.info("[Mock ADB] Key event: HOME")
        self.running_package = "com.android.launcher3"
        return True

    def key_recent_apps(self) -> bool:
        logger.info("[Mock ADB] Key event: RECENT_APPS")
        return True

    def screenshot(self, local_path: str) -> bool:
        logger.info(f"[Mock ADB] Saving mock screenshot to {local_path}")
        # Write dummy png bytes
        dummy_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00"
            b"\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        try:
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(dummy_png)
            return True
        except Exception:
            return False


class MockUIElement:
    def __init__(self, element_id: str, element_type: str, text: str, content_desc: str, clickable: bool, scrollable: bool, editable: bool, bounds: dict):
        self.element_id = element_id
        self.element_type = element_type
        self.text = text
        self.content_desc = content_desc
        self.clickable = clickable
        self.scrollable = scrollable
        self.editable = editable
        self.bounds = bounds

    def to_dict(self) -> dict:
        return {
            "id": self.element_id,
            "type": self.element_type,
            "text": self.text,
            "content_desc": self.content_desc,
            "clickable": self.clickable,
            "scrollable": self.scrollable,
            "editable": self.editable,
            "bounds": self.bounds
        }


class MockDriver:
    def __init__(self, serial: str):
        self.serial = serial
        self.current_screen = "settings"  # settings | bluetooth | playstore
        self.typed_text = ""

    @property
    def window_size(self) -> tuple[int, int]:
        return (1080, 1920)

    def get_tree(self) -> list[dict]:
        elements = []
        if self.current_screen == "settings":
            elements = [
                MockUIElement("com.android.settings:id/title", "TextView", "Settings", "", False, False, False, {"left": 0, "top": 0, "right": 100, "bottom": 50}),
                MockUIElement("com.android.settings:id/bluetooth", "TextView", "Bluetooth", "", True, False, False, {"left": 0, "top": 60, "right": 200, "bottom": 110})
            ]
        elif self.current_screen == "bluetooth":
            elements = [
                MockUIElement("com.android.settings:id/title", "TextView", "Bluetooth", "", False, False, False, {"left": 0, "top": 0, "right": 100, "bottom": 50}),
                MockUIElement("com.android.settings:id/toggle", "Switch", "Use Bluetooth", "", True, False, False, {"left": 0, "top": 60, "right": 200, "bottom": 110})
            ]
        elif self.current_screen == "playstore":
            elements = [
                MockUIElement("com.android.vending:id/search_bar", "EditText", "Search for apps", "Search", True, False, True, {"left": 0, "top": 0, "right": 300, "bottom": 50}),
                MockUIElement("com.android.vending:id/install_btn", "Button", "Install", "", True, False, False, {"left": 0, "top": 60, "right": 100, "bottom": 110})
            ]
        return [el.to_dict() for el in elements]

    def tap(self, element: dict) -> dict:
        logger.info(f"[Mock Driver] Tapping element: {element}")
        if element.get("text") == "Bluetooth":
            self.current_screen = "bluetooth"
        return {"success": True, "matched_element": element.get("id")}

    def type_text(self, text: str, clear_first: bool = True) -> dict:
        logger.info(f"[Mock Driver] Typing text: {text}")
        self.typed_text = text
        return {"success": True}

    def swipe(self, direction: str, distance: int = 500, speed: int = 300) -> dict:
        logger.info(f"[Mock Driver] Swiping {direction}")
        return {"success": True}

    def scroll_to(self, text: str) -> dict:
        logger.info(f"[Mock Driver] Scrolling to text: {text}")
        return {"success": True, "found": True}


class SessionManager:
    @staticmethod
    def start_session(db: DBSession, session_id: str, emulator_serial: Optional[str] = None) -> Session:
        statement = select(Session).where(Session.id == session_id)
        session = db.exec(statement).first()
        if session:
            raise ValueError(f"Session {session_id} already exists")
        
        serial = emulator_serial or os.getenv("VRSKI_EMULATOR_SERIAL", "emulator-5554")
        simulate = os.getenv("VRSKI_SIMULATE", "false").lower() in ("true", "1", "yes")
        
        driver = None
        adb_client = None
        
        if not simulate:
            try:
                if UIDriver is not None:
                    driver = UIDriver(serial)
                else:
                    logger.warning("UIDriver not available, falling back to mock driver.")
                    
                if ADBClient is not None:
                    adb_client = ADBClient(serial)
                else:
                    logger.warning("ADBClient not available, falling back to mock ADB client.")
            except Exception as e:
                logger.warning(f"Failed to connect to real emulator {serial}: {e}. Falling back to mock.")
                simulate = True

        if simulate or driver is None or adb_client is None:
            logger.info(f"Starting session {session_id} in simulated mode.")
            driver = MockDriver(serial)
            adb_client = MockADBClient(serial)
            _simulated_sessions[session_id] = True
        else:
            _simulated_sessions[session_id] = False

        _active_drivers[session_id] = driver
        _active_adb_clients[session_id] = adb_client
        
        session = Session(
            id=session_id,
            emulator_serial=serial,
            status="ready",
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
            
        return session

    @staticmethod
    def get_session(db: DBSession, session_id: str) -> Optional[Session]:
        statement = select(Session).where(Session.id == session_id)
        session = db.exec(statement).first()
        if session:
            session.last_active = datetime.utcnow()
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def update_session(db: DBSession, session_id: str, current_app: Optional[str] = None, status: Optional[str] = None) -> Optional[Session]:
        statement = select(Session).where(Session.id == session_id)
        session = db.exec(statement).first()
        if session:
            if current_app is not None:
                session.current_app = current_app
            if status is not None:
                session.status = status
            session.last_active = datetime.utcnow()
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    @staticmethod
    def end_session(db: DBSession, session_id: str) -> Optional[Session]:
        statement = select(Session).where(Session.id == session_id)
        session = db.exec(statement).first()
        if session:
            _active_drivers.pop(session_id, None)
            _active_adb_clients.pop(session_id, None)
            _simulated_sessions.pop(session_id, None)
            
            db.delete(session)
            db.commit()
            return session
        return None

    @staticmethod
    def get_driver(session_id: str) -> Any:
        return _active_drivers.get(session_id)

    @staticmethod
    def get_adb_client(session_id: str) -> Any:
        return _active_adb_clients.get(session_id)

    @staticmethod
    def is_simulated(session_id: str) -> bool:
        return _simulated_sessions.get(session_id, False)
