# Phase 6 — Concurrency, Scale & Performance (single-host)

**Goal:** Go from one agent / one phone to **many isolated sessions on one host**, and make
the loop fast and durable.

**Why now / risk retired:** The README already promises "multiple sessions, unlimited
agents" — today that's marketing (one emulator, global driver maps). Make it true. Because
the end game is open-source / self-hosted, this is about robust **local** multi-session and
multiple devices, **not** a cloud SaaS.

**Depends on:** Phase 1 (mostly). Benefits from Phase 3 (per-session isolation & audit).

---

## Scope
- [ ] **Multiple emulators/devices + a session pool**, with per-owner / per-session
  **isolation** — separate accounts, app data, and audit trails; no cross-talk.
- [ ] **Performance** — faster and/or cached tree dumps, fewer round-trips, a parallel-safe
  driver layer (today's in-memory global maps need to become per-session).
- [ ] **Lifecycle & recovery** — boot/reset/snapshot management, auto-heal on ADB drop (the
  keep-alive exists; generalize it), resource limits so one host doesn't fall over.

## Explicitly out of scope
- Cloud / multi-tenant SaaS (parked — see ROADMAP appendix). This phase ends at "rock-solid
  on a single beefy machine with several devices."

## Exit criteria (measurable)
- [ ] **N concurrent, isolated sessions** on one host run **stably over a long run**, with
  bounded, predictable resource use.
- [ ] Two sessions driving two apps **never** leak state or audit into each other.

## Key risks & open questions
- **Emulator resource cost** — each AVD is heavy (RAM/CPU); how many fit on a realistic dev
  machine? Measure early.
- **uiautomator2 throughput** under parallelism — the atx-agent model may bottleneck.
- *Open:* is there a lighter device target than full emulators for some workloads (e.g.
  headless containers)? Investigate without committing.
