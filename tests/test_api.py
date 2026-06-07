import os
# Set environment variables for testing before importing the app
db_file = "test_vrski.db"
if os.path.exists(db_file):
    try:
        os.remove(db_file)
    except Exception:
        pass
os.environ["VRSKI_DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ["VRSKI_SIMULATE"] = "true"

from fastapi.testclient import TestClient
from vrski.api.main import app
from vrski.session.db import init_db

client = TestClient(app)

def test_api_lifecycle():
    # Initialize SQLite database (file-based)
    from vrski.session.db import engine
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    init_db()
    
    # 1. Start session
    response = client.post("/session/start", json={"session_id": "test_session_1"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["session_id"] == "test_session_1"
    assert res_data["status"] == "ready"
    assert "emulator_serial" in res_data
    
    # 2. Get session status
    response = client.get("/session/test_session_1/status")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["session_id"] == "test_session_1"
    assert res_data["status"] == "ready"
    assert res_data["current_app"] == "com.android.settings"
    
    # 3. Get screen tree
    response = client.get("/session/test_session_1/screen")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "elements" in res_data
    assert len(res_data["elements"]) > 0
    # First screen is settings, so title should be Settings
    assert res_data["elements"][0]["text"] == "Settings"
    assert res_data["package"] == "com.android.settings"
    
    # 4. Tap "Bluetooth" element
    response = client.post("/session/test_session_1/action", json={
        "type": "tap",
        "text": "Bluetooth"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["matched_element"] == "com.android.settings:id/bluetooth"
    
    # 5. Get screen tree again (should be transitioned to Bluetooth screen)
    response = client.get("/session/test_session_1/screen")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["elements"][0]["text"] == "Bluetooth"
    assert res_data["elements"][1]["type"] == "Switch"
    
    # 6. Type action
    response = client.post("/session/test_session_1/action", json={
        "type": "type",
        "text": "testing search",
        "clear_first": True
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    
    # 7. Swipe action
    response = client.post("/session/test_session_1/action", json={
        "type": "swipe",
        "direction": "up",
        "distance": 300,
        "speed": 100
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    
    # 8. Scroll action
    response = client.post("/session/test_session_1/action", json={
        "type": "scroll_to",
        "text": "Use Bluetooth"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    
    # 9. Keypress actions: back, home, recent_apps
    for action_type in ["back", "home", "recent_apps"]:
        response = client.post("/session/test_session_1/action", json={"type": action_type})
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["success"] is True
        
    # 10. Play Store Authenticate
    response = client.post("/session/test_session_1/auth/playstore", json={
        "gmail": "vrski.agent@gmail.com",
        "password": "agentpassword123"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["account"] == "vrski.agent@gmail.com"
    
    # 11. Install app
    response = client.post("/session/test_session_1/install", json={
        "package_name": "com.instagram.android"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["package_name"] == "com.instagram.android"
    assert "duration_seconds" in res_data
    
    # 12. Launch app
    response = client.post("/session/test_session_1/launch", json={
        "package_name": "com.instagram.android"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    
    # Verify current_app status update
    response = client.get("/session/test_session_1/status")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["current_app"] == "com.instagram.android"
    
    # 13. Close app
    response = client.post("/session/test_session_1/close", json={
        "package_name": "com.instagram.android"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    
    # 14. End session
    response = client.post("/session/test_session_1/end")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["status"] == "ended"
    
    # 15. Verify session is no longer accessible
    response = client.get("/session/test_session_1/status")
    assert response.status_code == 404
    res_data = response.json()
    assert res_data["success"] is False
    assert "not found" in res_data["error"]

    pass

def test_api_negative_cases():
    # Initialize SQLite database (file-based)
    from vrski.session.db import engine
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    init_db()
    
    # 1. Duplicate session starts
    # Start session first time
    response = client.post("/session/start", json={"session_id": "neg_session_1"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Start session with same ID again
    response = client.post("/session/start", json={"session_id": "neg_session_1"})
    assert response.status_code == 400
    res_data = response.json()
    assert res_data["success"] is False
    assert "already exists" in res_data["error"]
    
    # 2. Nonexistent session actions
    # Status check
    response = client.get("/session/nonexistent_session/status")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Screen check
    response = client.get("/session/nonexistent_session/screen")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Action check
    response = client.post("/session/nonexistent_session/action", json={"type": "back"})
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Install check
    response = client.post("/session/nonexistent_session/install", json={"package_name": "com.whatsapp"})
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Launch check
    response = client.post("/session/nonexistent_session/launch", json={"package_name": "com.whatsapp"})
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Close check
    response = client.post("/session/nonexistent_session/close", json={"package_name": "com.whatsapp"})
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # Playstore authentication check
    response = client.post("/session/nonexistent_session/auth/playstore", json={"gmail": "a@b.com", "password": "123"})
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]
    
    # End session check
    response = client.post("/session/nonexistent_session/end")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "not found" in response.json()["error"]

    # 3. Invalid actions
    # Type validation error (422) for invalid action type
    response = client.post("/session/neg_session_1/action", json={"type": "invalid_type"})
    assert response.status_code == 422
    
    # Swipe action without direction
    response = client.post("/session/neg_session_1/action", json={"type": "swipe"})
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "direction is required" in response.json()["error"]
    
    # Type action without text
    response = client.post("/session/neg_session_1/action", json={"type": "type"})
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "text is required" in response.json()["error"]
    
    # Scroll_to action without text
    response = client.post("/session/neg_session_1/action", json={"type": "scroll_to"})
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "text is required" in response.json()["error"]
    
    # Tap action without element reference or coordinates
    response = client.post("/session/neg_session_1/action", json={"type": "tap"})
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "either coordinates" in response.json()["error"]

    # 4. Duplicate app installs
    # First install should succeed
    response = client.post("/session/neg_session_1/install", json={"package_name": "com.whatsapp"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Second install of same package should fail as duplicate
    response = client.post("/session/neg_session_1/install", json={"package_name": "com.whatsapp"})
    assert response.status_code == 400
    assert response.json()["success"] is False
    assert "already installed" in response.json()["error"]
    
    # End session
    response = client.post("/session/neg_session_1/end")
    assert response.status_code == 200
    assert response.json()["success"] is True

    pass

def test_api_new_validations():
    # Initialize SQLite database (file-based)
    from vrski.session.db import engine
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    init_db()

    # Start session
    response = client.post("/session/start", json={"session_id": "val_session"})
    assert response.status_code == 200

    # 1. Tap action with negative x coordinate
    response = client.post("/session/val_session/action", json={
        "type": "tap",
        "x": -10,
        "y": 20
    })
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "x" in response.json()["error"] or "Validation error" in response.json()["error"]

    # 2. Tap action with only x coordinate
    response = client.post("/session/val_session/action", json={
        "type": "tap",
        "x": 10
    })
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "both x and y must be provided" in response.json()["error"]

    # 3. Swipe action with invalid direction
    response = client.post("/session/val_session/action", json={
        "type": "swipe",
        "direction": "diagonal"
    })
    assert response.status_code == 422
    assert response.json()["success"] is False

    # 4. Swipe action with negative speed
    response = client.post("/session/val_session/action", json={
        "type": "swipe",
        "direction": "up",
        "speed": -50
    })
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "speed" in response.json()["error"] or "Validation error" in response.json()["error"]

    # 5. Swipe action with zero distance
    response = client.post("/session/val_session/action", json={
        "type": "swipe",
        "direction": "left",
        "distance": 0
    })
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert "distance" in response.json()["error"] or "Validation error" in response.json()["error"]

    # End session
    client.post("/session/val_session/end")
