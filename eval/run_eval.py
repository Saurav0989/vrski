#!/usr/bin/env python3
"""Vrski eval harness.

Runs the golden flows against a live Vrski API and reports a success rate. This is
the regression net for reliability — "better and better" only means something if we
can watch this number move. Run with the emulator + API up:

    python3 eval/run_eval.py --repeats 3

Exit criterion (Phase 1): >= 4 apps covered and overall pass rate >= 90%.
"""
import os
import sys
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden_flows import FLOWS  # noqa: E402

BASE = os.environ.get("VRSKI_API_URL", "http://localhost:7070")
SER = os.environ.get("VRSKI_EMULATOR_SERIAL", "emulator-5554")


def _adb(*a):
    return subprocess.run(["adb", "-s", SER] + list(a), capture_output=True, text=True).stdout


def _req(method, path, body=None, timeout=90):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {"success": False, "error": f"HTTP {e.code}"}


def post(p, b=None):
    return _req("POST", p, b)


def get(p):
    return _req("GET", p)


def _screen_texts(sid):
    scr = get(f"/session/{sid}/screen")
    texts = []
    for e in scr.get("elements", []):
        if e.get("text"):
            texts.append(e["text"])
        if e.get("content_desc"):
            texts.append(e["content_desc"])
    return scr, texts


def assert_any(sid, needles, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        _, texts = _screen_texts(sid)
        joined = " || ".join(texts).lower()
        for n in needles:
            if n.lower() in joined:
                return True, n
        time.sleep(1.0)
    return False, None


def assert_activity(sid, contains, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        scr = get(f"/session/{sid}/screen")
        act = scr.get("activity", "") or ""
        if contains.lower() in act.lower():
            return True, act
        time.sleep(1.0)
    return False, get(f"/session/{sid}/screen").get("activity")


def run_step(sid, step):
    do = step["do"]
    if do == "launch":
        post(f"/session/{sid}/close", {"package_name": step["package"]})
        time.sleep(0.8)
        if step.get("activity"):
            # explicit activity via adb is more reliable than monkey on this emulator
            _adb("shell", "am", "start", "-n", f"{step['package']}/{step['activity']}")
        else:
            post(f"/session/{sid}/launch", {"package_name": step["package"]})
        return True, ""
    if do == "wait_stable":
        post(f"/session/{sid}/wait_stable", {"timeout": step.get("timeout", 10), "settle_ms": step.get("settle_ms", 400)})
        return True, ""
    if do == "dismiss":
        for _ in range(step.get("times", 2)):
            post(f"/session/{sid}/dismiss_popups")
            time.sleep(0.4)
        return True, ""
    if do == "tap":
        body = {"type": "tap"}
        for k in ("text", "content_desc", "element_id", "x", "y"):
            if k in step:
                body[k] = step[k]
        r = post(f"/session/{sid}/action", body)
        if not r.get("success"):
            # One retry after letting the screen settle — a target may not have
            # rendered yet. Mirrors how a real agent recovers from a transient miss.
            post(f"/session/{sid}/wait_stable", {"timeout": 5, "settle_ms": 500})
            r = post(f"/session/{sid}/action", body)
        return bool(r.get("success")), ("" if r.get("success") else f"tap failed: {r.get('error', '')}")
    if do == "type":
        r = post(f"/session/{sid}/action", {"type": "type", "text": step["text"], "clear_first": step.get("clear_first", True)})
        return bool(r.get("success")), ("" if r.get("success") else f"type failed: {r.get('error', '')}")
    if do == "back":
        post(f"/session/{sid}/action", {"type": "back"})
        return True, ""
    if do == "assert_text":
        ok, hit = assert_any(sid, step["any"], step.get("timeout", 8))
        return ok, ("" if ok else f"none of {step['any']} appeared")
    if do == "assert_activity":
        ok, act = assert_activity(sid, step["contains"], step.get("timeout", 8))
        return ok, ("" if ok else f"activity not *{step['contains']}* (was {act})")
    return False, f"unknown step '{do}'"


def run_flow(sid, flow):
    for i, step in enumerate(flow["steps"]):
        ok, err = run_step(sid, step)
        if not ok:
            return False, f"step {i} ({step['do']}): {err}"
        time.sleep(0.3)
    return True, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--session", default="eval")
    args = ap.parse_args()
    sid = args.session

    post("/session/start", {"session_id": sid})  # no-op if it already exists

    results = []
    print(f"\nVrski eval — {len(FLOWS)} flows x {args.repeats} repeats\n" + "-" * 64)
    for flow in FLOWS:
        for _ in range(args.repeats):
            t0 = time.time()
            try:
                ok, err = run_flow(sid, flow)
            except Exception as e:
                ok, err = False, f"exception: {e}"
            dt = round(time.time() - t0, 1)
            results.append({"app": flow["app"], "name": flow["name"], "ok": ok, "err": err, "sec": dt})
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}] {flow['app']:10} {flow['name']:28} {dt:>5}s {'' if ok else '— ' + err}")

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    rate = (passed / total * 100) if total else 0.0
    apps = sorted({r["app"] for r in results})
    apps_all_pass = sorted({r["app"] for r in results} - {r["app"] for r in results if not r["ok"]})

    print("-" * 64)
    print("Per-app:")
    for app in apps:
        runs = [r for r in results if r["app"] == app]
        p = sum(1 for r in runs if r["ok"])
        print(f"  {app:10} {p}/{len(runs)}")
    print("-" * 64)
    print(f"Overall: {passed}/{total} = {rate:.0f}%   apps covered: {len(apps)}   apps fully green: {len(apps_all_pass)}")
    ok_exit = len(apps) >= 4 and rate >= 90.0
    print(f"Phase-1 exit criterion (>=4 apps, >=90%): {'MET ✅' if ok_exit else 'NOT MET ❌'}")
    print(json.dumps({"overall_rate": rate, "passed": passed, "total": total, "apps": len(apps)}))
    return 0 if ok_exit else 1


if __name__ == "__main__":
    sys.exit(main())
