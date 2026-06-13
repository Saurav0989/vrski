# Phase 3 — Trust, Control & Audit

**Goal:** The owner is in control of anything sensitive, and every action is recorded and
replayable.

**Why now / risk retired:** You chose to build trust **early**, and the very next phase
(food delivery) reaches a real payment screen. This layer **must** precede any real-money
flow. It's also a headline feature for adoption: *"an agent literally cannot spend your
money or do something irreversible without your explicit yes."*

**Depends on:** Phase 1 (honest signals), Phase 2 (identity).

---

## Scope
- [ ] **Action classification.** Tag every action as **safe** vs **sensitive** (spend, send /
  post, delete, irreversible). Driven by heuristics + per-app recipe hints (recipes arrive in
  Phase 4; design the hook now).
- [ ] **Approval protocol (harness-agnostic).** On a sensitive action, Vrski **pauses** and
  returns a structured "approval required" payload — *what, where, how much, screenshot*. Only
  an explicit owner-approval token lets it proceed. Works over MCP so any harness (Hermes,
  Claude Code, …) can render the prompt.
- [ ] **Policy engine.** Per-app allowlists, **spend caps** (e.g. ≤ ₹X per order / per day),
  blocked actions, and a **dry-run mode** that narrates what it *would* do without executing.
- [ ] **Audit trail.** Promote the existing structured logging into a first-class, queryable,
  **replayable** record: every action, its params, result, screenshot, and the
  approve/deny decision — per session.
- [ ] **Kill-switch / pause.** The owner can freeze a session instantly.

## Explicitly out of scope
- The specific vertical flows themselves (Phase 4) — this phase only governs *how* sensitive
  steps are gated and recorded.

## Exit criteria (measurable)
- [ ] A "place order / pay"-style action **cannot execute** without an explicit owner approval
  surfaced through the harness.
- [ ] A **spend cap is enforced** — an over-cap action is blocked.
- [ ] Every session yields a **complete audit log** that can be replayed step by step.

## Key risks & open questions
- **Classifying "sensitive" reliably** across unknown apps is hard — start conservative
  (default-deny on anything that looks like pay/confirm/submit) and let recipes refine it.
- **Approval UX must not be annoying** or owners will route around it. *Open:* where does
  approval surface — harness chat, a push notification, both? Define a protocol; let harnesses
  choose how to render it.
- Balancing autonomy vs control — too many prompts kills the magic; too few kills the trust.
