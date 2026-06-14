"""Phase 3 — trust, control & audit.

Gates sensitive / irreversible actions behind owner approval, enforces simple policy
(blocked labels, dry-run, a per-session rate cap, pause/kill-switch), and writes a
replayable, **secret-free** audit log per session.

Design: the agent drives by tool calls; the moment a *commit* happens is a TAP on a
button like "Pay", "Place order", "Send", or "Delete". So we classify and gate taps.
Sensitive taps are not executed — they return `approval_required` with a screenshot,
and only an explicit `approve` (the owner's yes, surfaced by the harness) runs them.
We never store or log secrets.
"""
import os
import json
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

# --- sensitivity classification ---------------------------------------------

# Erring toward "sensitive" is the safe failure mode — an extra approval prompt
# beats an un-approved payment. Matched as a substring of the tap's label.
SENSITIVE_KEYWORDS: Dict[str, List[str]] = {
    "spend": [
        "pay", "pay now", "place order", "place your order", "buy", "checkout",
        "check out", "purchase", "confirm order", "confirm payment", "complete order",
        "complete purchase", "order now", "subscribe", "donate", "transfer",
        "send money", "top up", "add card", "submit order", "proceed to pay",
        "continue to payment", "agree & pay",
    ],
    "send": ["send", "post", "publish", "share", "tweet", "confirm and send"],
    "destructive": [
        "delete", "remove", "deactivate", "close account", "unfriend", "block",
        "clear all", "discard", "cancel order", "cancel subscription", "unsubscribe",
    ],
}


def classify_action(action_type: str, text: str = "", content_desc: str = "") -> Dict[str, Any]:
    """Classify a *tap* target as safe vs sensitive. Only taps commit things."""
    if action_type != "tap":
        return {"sensitive": False, "category": None, "matched": None}
    label = ((text or "") + " " + (content_desc or "")).strip().lower()
    if not label:
        return {"sensitive": False, "category": None, "matched": None}
    for category, kws in SENSITIVE_KEYWORDS.items():
        for kw in kws:
            if kw in label:
                return {"sensitive": True, "category": category, "matched": kw}
    return {"sensitive": False, "category": None, "matched": None}


# --- policy + per-session control state --------------------------------------

@dataclass
class Policy:
    require_approval_for_sensitive: bool = True
    dry_run: bool = False                                   # narrate, never execute
    blocked_labels: List[str] = field(default_factory=list)  # never execute, even if approved
    max_sensitive_actions: Optional[int] = None             # per-session rate cap


@dataclass
class ControlState:
    policy: Policy = field(default_factory=Policy)
    paused: bool = False
    sensitive_count: int = 0
    pending: Dict[str, Any] = field(default_factory=dict)


_states: Dict[str, ControlState] = {}
_lock = threading.Lock()


def _audit_path(session_id: str) -> str:
    d = os.getenv("VRSKI_AUDIT_DIR", "audit")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{session_id}.jsonl")


class ControlManager:
    @staticmethod
    def get(session_id: str) -> ControlState:
        with _lock:
            if session_id not in _states:
                _states[session_id] = ControlState()
            return _states[session_id]

    @staticmethod
    def set_policy(session_id: str, **kwargs) -> Policy:
        p = ControlManager.get(session_id).policy
        for k, v in kwargs.items():
            if v is not None and hasattr(p, k):
                setattr(p, k, v)
        ControlManager.audit(session_id, {"kind": "policy_set", "policy": asdict(p)})
        return p

    @staticmethod
    def set_paused(session_id: str, paused: bool) -> None:
        ControlManager.get(session_id).paused = bool(paused)
        ControlManager.audit(session_id, {"kind": "paused" if paused else "resumed"})

    @staticmethod
    def audit(session_id: str, entry: Dict[str, Any]) -> None:
        record = {"ts": round(time.time(), 3), **entry}
        try:
            with open(_audit_path(session_id), "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    @staticmethod
    def read_audit(session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        path = _audit_path(session_id)
        if not os.path.exists(path):
            return []
        out: List[Dict[str, Any]] = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            return []
        return out[-limit:]

    @staticmethod
    def create_pending(session_id: str, action: Dict[str, Any], meta: Dict[str, Any]) -> str:
        st = ControlManager.get(session_id)
        pid = uuid.uuid4().hex[:12]
        st.pending[pid] = {"action": action, "meta": meta, "ts": time.time()}
        return pid

    @staticmethod
    def pop_pending(session_id: str, pid: str) -> Optional[Dict[str, Any]]:
        return ControlManager.get(session_id).pending.pop(pid, None)

    @staticmethod
    def note_sensitive_executed(session_id: str) -> None:
        ControlManager.get(session_id).sensitive_count += 1

    @staticmethod
    def gate(session_id: str, action_type: str, text: str = "", content_desc: str = "") -> Dict[str, Any]:
        """Decide what to do with an action *before* executing it.

        Returns {"decision": one of allow|approval|dry_run|blocked, ...}.
        """
        st = ControlManager.get(session_id)
        label = ((text or "") + " " + (content_desc or "")).strip().lower()

        if st.paused:
            return {"decision": "blocked", "reason": "paused",
                    "message": "Session is paused by the owner. Resume to continue."}

        for bl in st.policy.blocked_labels:
            if bl and bl.lower() in label:
                return {"decision": "blocked", "reason": "blocked_label", "matched": bl,
                        "message": f"Action matching '{bl}' is blocked by policy."}

        cls = classify_action(action_type, text, content_desc)
        if cls["sensitive"]:
            cap = st.policy.max_sensitive_actions
            if cap is not None and st.sensitive_count >= cap:
                return {"decision": "blocked", "reason": "rate_cap", "category": cls["category"],
                        "message": f"Sensitive-action cap ({cap}) reached for this session."}
            if st.policy.dry_run:
                return {"decision": "dry_run", "category": cls["category"], "matched": cls["matched"]}
            if st.policy.require_approval_for_sensitive:
                return {"decision": "approval", "category": cls["category"], "matched": cls["matched"]}
        return {"decision": "allow", "sensitive": cls["sensitive"]}
