# Phase 2 — Identity & the One-Time Login Pattern

**Goal:** Generalize "the human logs in once, the agent uses it forever" from Google to
**any** app, and handle the human-only walls (OTP / 2FA / CAPTCHA) cleanly.

**Why now / risk retired:** Food, rides, and comms all require being logged into that
*specific* app. Without a durable, safe login pattern, no real vertical is possible — and
the agent must never be the thing that handles passwords or 2FA codes.

**Depends on:** Phase 1 (a reliable loop to drive login screens).

---

## Scope
- [ ] **Per-app one-time login mode.** A guided flow where the owner logs into `<app>` once
  (emulator window visible), mirroring today's Google sign-in but generalized to any app.
- [ ] **State persistence.** Snapshot / back up the logged-in state so it survives emulator
  restarts and resets (extend the existing Google-login snapshot approach to arbitrary apps).
- [ ] **Wall detection & hand-back protocol.** Detect OTP, 2FA, CAPTCHA, "verify it's you" →
  pause and surface a structured "owner action needed" to the harness → resume after the
  owner clears it. (We already do this for Google; make it a general primitive.)
- [ ] **Secret hygiene.** Any credentials the owner provides are stored locally and **never**
  sent to the model or written to agent-visible logs. The agent never sees passwords or OTPs.
- [ ] **Identity model.** Track which Google account and which app logins exist, per owner /
  per session.

## Explicitly out of scope
- *What to do* inside the app (verticals — Phase 4+); spend approval (Phase 3).

## Exit criteria (measurable)
- [ ] Owner logs into a target app (e.g. Swiggy) **once**; the agent operates it across
  emulator restarts with **no re-login**.
- [ ] An OTP/2FA wall hit **mid-flow** is detected and handed back to the owner, and the flow
  **resumes** afterward.
- [ ] **No secret** ever appears in agent-visible context or logs (audited).

## Key risks & open questions
- **Login durability** across app updates and token expiry — how often does re-login actually
  get forced? Needs real measurement per app.
- **Anti-automation / emulator detection** — some apps resist automation or flag emulators.
  This may first bite here (login) and again in Phase 4; may eventually motivate real-device
  support.
- *Open:* snapshot the whole emulator vs back up per-app data — which is more robust and
  portable?
