#!/usr/bin/env python3
"""Run a Vrski recipe against the live device — also how you tune recipes.

    python3 eval/run_recipe.py clock_start_timer --param minutes=5
    python3 eval/run_recipe.py contacts_add --param name="Alex Rivera"

Recipes run through the normal Vrski API, so the Phase 3 trust gate applies: a
sensitive step returns approval_required and the recipe stops (the owner must approve).
"""
import os
import sys
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vrski.recipes import RECIPES, render_flow, fill  # noqa: E402

BASE = os.environ.get("VRSKI_API_URL", "http://localhost:7070")
SER = os.environ.get("VRSKI_EMULATOR_SERIAL", "emulator-5554")
SID = os.environ.get("VRSKI_SESSION", "owner")


def adb(*a):
    return subprocess.run(["adb", "-s", SER] + list(a), capture_output=True, text=True).stdout


def api(method, path, body=None, timeout=90):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"success": False, "error": f"HTTP {e.code}"}


def assert_text(needles, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        scr = api("GET", f"/session/{SID}/screen")
        blob = " || ".join(((e.get('text') or '') + " " + (e.get('content_desc') or '')) for e in scr.get('elements', [])).lower()
        for n in needles:
            if n.lower() in blob:
                return True, n
        time.sleep(1.0)
    return False, None


def run_step(step):
    do = step["do"]
    if do == "dismiss":
        for _ in range(step.get("times", 2)):
            api("POST", f"/session/{SID}/dismiss_popups")
            time.sleep(0.3)
        return True, ""
    if do == "wait_stable":
        api("POST", f"/session/{SID}/wait_stable", {"timeout": step.get("timeout", 10), "settle_ms": step.get("settle_ms", 500)})
        return True, ""
    if do == "tap":
        body = {"type": "tap"}
        for k in ("text", "content_desc", "element_id", "x", "y"):
            if k in step:
                body[k] = step[k]
        r = api("POST", f"/session/{SID}/action", body)
        if r.get("approval_required"):
            return False, f"needs owner approval: {r.get('what')} (pending {r.get('pending_id')})"
        if not r.get("success"):  # one retry after settling
            api("POST", f"/session/{SID}/wait_stable", {"timeout": 5})
            r = api("POST", f"/session/{SID}/action", body)
        return bool(r.get("success")), ("" if r.get("success") else f"tap failed: {r.get('error', '')}")
    if do == "type":
        r = api("POST", f"/session/{SID}/action", {"type": "type", "text": step.get("text", ""), "clear_first": step.get("clear_first", True)})
        return bool(r.get("success")), ("" if r.get("success") else f"type failed: {r.get('error', '')}")
    if do == "back":
        api("POST", f"/session/{SID}/action", {"type": "back"})
        return True, ""
    if do == "scroll_to":
        # best-effort scroll toward the target; the following tap validates it
        api("POST", f"/session/{SID}/action", {"type": "scroll_to", "text": step["text"]})
        return True, ""
    if do == "assert_text":
        ok, _ = assert_text(step["any"], step.get("timeout", 8))
        return ok, ("" if ok else f"none of {step['any']}")
    return False, f"unknown step '{do}'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe")
    ap.add_argument("--param", action="append", default=[], help="key=value")
    args = ap.parse_args()
    params = dict(p.split("=", 1) for p in args.param)
    rc = RECIPES[args.recipe]

    print(f"Recipe: {rc.name} — {rc.app}")
    api("POST", "/session/start", {"session_id": SID})

    # reliable launch (explicit activity beats monkey on this emulator)
    adb("shell", "am", "force-stop", rc.package)
    time.sleep(1)
    if rc.launch_activity:
        adb("shell", "am", "start", "-n", f"{rc.package}/{rc.launch_activity}")
    else:
        adb("shell", "monkey", "-p", rc.package, "-c", "android.intent.category.LAUNCHER", "1")
    api("POST", f"/session/{SID}/wait_stable", {"timeout": 18, "settle_ms": 1500})

    for i, step in enumerate(render_flow(rc, params)):
        ok, err = run_step(step)
        detail = {k: v for k, v in step.items() if k != "do"}
        print(f"  [{'ok ' if ok else 'FAIL'}] {step['do']:12} {detail} {'' if ok else '— ' + err}")
        if not ok:
            print(f"STOPPED at step {i}")
            return 1
        time.sleep(0.3)

    needles = [fill(s, params) for s in rc.success_any]
    ok, hit = assert_text(needles, 8)
    print(f"\nSUCCESS check {needles}: " + (f"PASS (matched {hit!r})" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
