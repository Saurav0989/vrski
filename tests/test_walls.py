"""Unit tests for login/verification wall classification."""
from vrski.walls import classify_wall


def test_bot_block_by_text():
    r = classify_wall(
        [{"text": "We've hit a roadblock"}, {"text": "Confirm that you're not a robot"}],
        "com.perimeterx.mobile_sdk.block.PXBlockActivity",
    )
    assert r["wall"] == "bot_block"
    assert r["human_required"] is True


def test_bot_block_by_activity():
    r = classify_wall([{"text": "loading"}], "com.app.PxBlockActivity")
    assert r["wall"] == "bot_block"
    assert r["human_required"] is True


def test_login_with_google_sso_is_agent_completable():
    r = classify_wall(
        [{"text": "Sign in or create an account"}, {"text": "Continue with Google"}, {"text": "Continue with Facebook"}],
        "LoginFlowActivity",
    )
    assert r["wall"] == "login"
    assert r["google_sso_available"] is True
    assert r["human_required"] is False


def test_login_without_sso_needs_human():
    r = classify_wall([{"text": "Log in"}, {"content_desc": "Email"}, {"text": "Continue"}], "LoginActivity")
    assert r["wall"] == "login"
    assert r["human_required"] is True


def test_otp_human_required():
    r = classify_wall([{"text": "Enter the 6-digit code we sent to your phone"}], "Verify")
    assert r["wall"] == "otp"
    assert r["human_required"] is True


def test_2fa_human_required():
    r = classify_wall([{"text": "Verify it's you"}], "")
    assert r["wall"] == "2fa"
    assert r["human_required"] is True


def test_no_wall():
    r = classify_wall([{"text": "Pizza Palace"}, {"text": "Order now"}], "HomeActivity")
    assert r["wall"] == "none"
    assert r["human_required"] is False
