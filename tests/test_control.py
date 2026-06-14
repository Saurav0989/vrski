"""Unit tests for the Phase 3 trust/control layer."""
import os
import tempfile

# Keep audit writes out of the repo during tests.
os.environ["VRSKI_AUDIT_DIR"] = tempfile.mkdtemp(prefix="vrski_audit_test_")

from vrski.control import classify_action, ControlManager  # noqa: E402


# --- classification ---------------------------------------------------------

def test_classify_pay_is_sensitive():
    r = classify_action("tap", "Pay $24.50")
    assert r["sensitive"] and r["category"] == "spend"


def test_classify_place_order():
    r = classify_action("tap", "Place order")
    assert r["sensitive"] and r["category"] == "spend"


def test_classify_send_by_content_desc():
    r = classify_action("tap", "", "Send")
    assert r["sensitive"] and r["category"] == "send"


def test_classify_delete_is_destructive():
    r = classify_action("tap", "Delete")
    assert r["sensitive"] and r["category"] == "destructive"


def test_classify_safe_label():
    assert not classify_action("tap", "Search")["sensitive"]


def test_type_is_never_classified_sensitive():
    assert not classify_action("type", "Pay")["sensitive"]


# --- gate decisions ---------------------------------------------------------

def test_gate_allows_safe():
    assert ControlManager.gate("t_allow", "tap", "Search")["decision"] == "allow"


def test_gate_requires_approval_for_sensitive():
    assert ControlManager.gate("t_appr", "tap", "Place order")["decision"] == "approval"


def test_gate_paused_blocks_everything():
    ControlManager.set_paused("t_pause", True)
    d = ControlManager.gate("t_pause", "tap", "Search")
    assert d["decision"] == "blocked" and d["reason"] == "paused"


def test_gate_dry_run():
    ControlManager.set_policy("t_dry", dry_run=True)
    assert ControlManager.gate("t_dry", "tap", "Pay")["decision"] == "dry_run"


def test_gate_blocked_label_never_runs():
    ControlManager.set_policy("t_block", blocked_labels=["delete"])
    d = ControlManager.gate("t_block", "tap", "Delete account")
    assert d["decision"] == "blocked" and d["reason"] == "blocked_label"


def test_gate_rate_cap_enforced():
    ControlManager.set_policy("t_cap", max_sensitive_actions=0)
    d = ControlManager.gate("t_cap", "tap", "Pay")
    assert d["decision"] == "blocked" and d["reason"] == "rate_cap"


def test_pending_roundtrip():
    pid = ControlManager.create_pending("t_pend", {"type": "tap", "text": "Pay"}, {"what": "tap Pay"})
    popped = ControlManager.pop_pending("t_pend", pid)
    assert popped["action"]["text"] == "Pay"
    assert ControlManager.pop_pending("t_pend", pid) is None  # one-shot


def test_audit_roundtrip():
    ControlManager.audit("t_audit", {"kind": "test_event", "detail": "hello"})
    log = ControlManager.read_audit("t_audit")
    assert any(e.get("kind") == "test_event" for e in log)


# --- integration: the full gated-tap round-trip through the real route code -----

class _FakeDriver:
    """Minimal driver that returns a fixed tree and records taps."""
    def __init__(self, tree):
        self._tree = tree
        self.taps = []

    def get_tree(self):
        return self._tree

    def tap(self, el):
        self.taps.append(el)
        return {"success": True}

    def get_screenshot_base64(self):
        return None


def test_sensitive_tap_is_blocked_until_approved_then_executes():
    """The core exit criterion: a sensitive action cannot execute without approval."""
    from vrski.api.routes.actions import do_semantic_tap

    sid = "t_roundtrip"
    tree = [{"text": "Send", "id": "btn_send", "content_desc": "", "clickable": True, "editable": False}]
    drv = _FakeDriver(tree)

    # 1. A sensitive tap returns approval_required and does NOT execute.
    r = do_semantic_tap(drv, sid, "Send", None, None)
    assert r.get("approval_required") is True
    assert r.get("pending_id")
    assert drv.taps == []  # nothing tapped

    # 2. The owner approves (bypass_gate) → it executes exactly once.
    pending = ControlManager.pop_pending(sid, r["pending_id"])
    assert pending is not None
    r2 = do_semantic_tap(drv, sid, pending["action"]["text"], None, None, bypass_gate=True)
    assert r2["success"] is True
    assert len(drv.taps) == 1


def test_safe_tap_executes_immediately():
    from vrski.api.routes.actions import do_semantic_tap

    drv = _FakeDriver([{"text": "Search", "id": "btn_search", "content_desc": "", "clickable": True, "editable": False}])
    r = do_semantic_tap(drv, "t_safe", "Search", None, None)
    assert r["success"] is True
    assert len(drv.taps) == 1  # safe action runs without approval


def test_blocked_label_never_executes_even_via_route():
    from vrski.api.routes.actions import do_semantic_tap

    sid = "t_blocked_route"
    ControlManager.set_policy(sid, blocked_labels=["Delete"])
    drv = _FakeDriver([{"text": "Delete", "id": "btn_del", "content_desc": "", "clickable": True, "editable": False}])
    r = do_semantic_tap(drv, sid, "Delete", None, None)
    assert r.get("blocked") is True and r.get("reason") == "blocked_label"
    assert drv.taps == []
