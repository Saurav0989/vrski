# Phase 4 — Vertical 1: Food Delivery (flagship) + the Vertical Playbook

**Goal:** Complete a real food order end to end (gated at payment), **and** extract a
reusable *Vertical Playbook* so the next app and the next vertical are cheap.

**Why now / risk retired:** Food delivery is your flagship "this is why Vrski matters,"
and it's the first task that exercises **every** prior phase at once — reliable loop (1),
being logged in (2), and owner-approved payment (3). It also forces us to invent the
**recipe** abstraction, which is the whole OSS scaling story.

**Depends on:** Phases 1, 2, 3.

---

## Scope
- [ ] **Drive a real food app** (Swiggy / Zomato / Uber Eats): launch (logged in) →
  set/confirm delivery address → search restaurant or dish → build cart → reach checkout →
  **owner-approval gate (Phase 3)** → optionally place the order.
- [ ] **The Vertical Playbook / recipe format.** A declarative spec per app — package name,
  deeplinks, key screens, known interstitials, sensitive-action hints, and a golden flow —
  that both the agent and the eval harness consume. This dovetails with Hermes "skills" and is
  the multiplier that makes "all the things" tractable.
- [ ] **Handle the mess:** promos/upsells, address & payment-method selection, out-of-stock
  items, surge/fees, and the inevitable interstitials.
- [ ] **Add the food-order golden flow to the eval harness.**

## Explicitly out of scope
- Other verticals (Phase 5). If something here needs a *core* change rather than recipe data,
  that's a signal to loop back to Phase 1/3 — note it, don't hack around it.

## Exit criteria (measurable)
- [ ] From a logged-in device, the agent completes a food order **up to the owner-approved
  payment step** on **≥1 app**, repeatably (tracked in the eval harness).
- [ ] A **second app in the same vertical** can be added as a **recipe only** — no core code
  changes — within a defined, small effort budget.

## Key risks & open questions
- **Anti-automation / emulator detection** by commercial apps is the biggest unknown — payment
  and login flows are exactly where apps fingerprint emulators. May force real-device support
  or a stealthier emulator config. *Surface this early on the real app.*
- **Payment screens** are the most sensitive *and* the most variable across apps/regions
  (India: UPI vs cards vs wallets) — lean hard on the Phase 3 gate and dry-run mode.
- **Region/app spread:** Swiggy/Zomato (India) vs Uber Eats (global) differ; the recipe format
  must absorb that without core forks.
