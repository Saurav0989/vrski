# Deployment & Scaling

Vrski is **self-hosted** — you run it on your own machine(s). This covers running it from
one device up to several, plus the real-device path that unlocks "hard mode."

## The default: one host, one device, one session

`scripts/start_vrski.sh` boots one emulator and the control API. One agent drives one phone
through one session (`owner`). This is the right setup for the long-tail assistant (see the
recipes in `vrski/recipes.py`), and for most users it's all they need.

## Multiple sessions / multiple devices on one host

Each session binds to a **device serial**, so N devices = N isolated sessions:

```python
# boot a second emulator on another port (needs its own AVD, or -read-only)
#   emulator -avd vrski_dev_2 -port 5556 ...

vrski_start_session("agentA", emulator_serial="emulator-5554")
vrski_start_session("agentB", emulator_serial="emulator-5556")

vrski_list_sessions()   # → each session with device, status, current app, live state
```

**Isolated per session:** its own uiautomator2 driver/device **and** its own trust state —
policy, pending approvals, pause/kill-switch, and audit log. Session A being paused or
hitting a spend cap never affects session B (covered by tests).

**Caveat — resources.** Each emulator is heavy (GBs of RAM, real CPU); one laptop fits only
a few (this one fell over once running a single emulator for hours). For many concurrent
agents, use a beefier host or real devices. This is single-host scaling, not a cloud service
(that's deliberately out of scope — see the roadmap appendix).

## Real devices (unlocks hard mode)

uiautomator2 + ADB are device-agnostic — a real phone works exactly like an emulator:

```python
# adb devices                      → find the serial, e.g. 39xxhz123
# adb connect <ip>:5555            → or ADB-over-Wi-Fi
vrski_start_session("owner", emulator_serial="39xxhz123")
```

A real device passes the **"device not compatible" / Play Integrity** checks the emulator
fails — the only way to even *install* some transactional apps (food / ride / banking; see
`HARD_MODE.md`).

**But:** behavioral anti-bot (PerimeterX, DataDome, …) and CAPTCHAs may *still* block a real
device, and we **never** try to evade them — Vrski detects the wall (`vrski_check_wall`) and
hands back to the owner. Some apps simply stay closed to automation, and that's acceptable.

Requirements: USB debugging on, the owner's apps logged in once (same one-time pattern as the
Google sign-in), and physical/network access to the device.

## Summary

| Setup | Use it for |
|-------|-----------|
| 1 emulator, 1 session | The long-tail assistant — most users |
| N emulators on a big host | A few concurrent, isolated agents |
| Real device(s) | Apps that reject the emulator; hard mode (with human-in-the-loop) |
| Cloud / multi-tenant SaaS | Out of scope (parked) |
