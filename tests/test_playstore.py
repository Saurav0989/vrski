import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

# Set environment variables for testing before importing the app
db_file = "test_vrski_playstore.db"
if os.path.exists(db_file):
    try:
        os.remove(db_file)
    except Exception:
        pass
os.environ["VRSKI_DATABASE_URL"] = f"sqlite:///{db_file}"
os.environ["VRSKI_SIMULATE"] = "true"

from vrski.api.main import app
from vrski.session.db import init_db, engine
from vrski.playstore.auth import signin_playstore, get_playstore_account
from vrski.playstore.installer import install_app


def test_playstore_unit_mock():
    # Setup test database
    SQLModel.metadata.drop_all(engine)
    init_db()

    client = TestClient(app)
    
    # Start a mock session via API
    resp = client.post("/session/start", json={"session_id": "ps_unit_session"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 1. Test unit get_playstore_account
    acc_res = get_playstore_account("ps_unit_session")
    assert acc_res["signed_in"] is True
    assert acc_res["account"] == "vrski.agent@gmail.com"

    # 2. Test unit signin_playstore
    signin_res = signin_playstore("ps_unit_session", "test.user@gmail.com", "secretpass")
    assert signin_res["success"] is True
    assert signin_res["account"] == "test.user@gmail.com"

    # 3. Test unit install_app
    install_res = install_app("ps_unit_session", "com.spotify.music")
    assert install_res["success"] is True
    assert install_res["package_name"] == "com.spotify.music"
    assert install_res["duration_seconds"] > 0

    # Clean up
    client.post("/session/ps_unit_session/end")


def test_playstore_api_auth_flow():
    SQLModel.metadata.drop_all(engine)
    init_db()

    client = TestClient(app)

    # 1. Start session
    resp = client.post("/session/start", json={"session_id": "ps_auth_session"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2. Query initial signed in account (should default to mock)
    resp = client.get("/session/ps_auth_session/auth/playstore")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["signed_in"] is True
    assert data["account"] == "vrski.agent@gmail.com"

    # 3. Post sign-in credentials
    resp = client.post("/session/ps_auth_session/auth/playstore", json={
        "gmail": "vrski.custom@gmail.com",
        "password": "supersecurepassword"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["account"] == "vrski.custom@gmail.com"

    # Clean up
    client.post("/session/ps_auth_session/end")


def test_playstore_api_install_flow():
    SQLModel.metadata.drop_all(engine)
    init_db()

    client = TestClient(app)

    # 1. Start session
    resp = client.post("/session/start", json={"session_id": "ps_install_session"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 2. Install app
    resp = client.post("/session/ps_install_session/install", json={
        "package_name": "com.twitter.android"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["package_name"] == "com.twitter.android"
    assert "duration_seconds" in data

    # 3. Verify it is registered as installed in current app list
    # Query status endpoint
    resp = client.get("/session/ps_install_session/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # Clean up
    client.post("/session/ps_install_session/end")
