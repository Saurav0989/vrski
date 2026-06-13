# Phase 5 — More Verticals: Rides → Comms → Expand

**Goal:** Prove the playbook by adding verticals with **minimal core change** — each new
vertical is a recipe plus, at most, one new shared primitive.

**Why now / risk retired:** This is the test of Phase 4's central bet. If adding "book a
ride" or "reply on WhatsApp" requires rewriting the core, the OSS-standard dream dies. If
it's mostly a recipe, Vrski scales to everything.

**Depends on:** Phase 4 (the playbook + recipe format).

---

## Scope
- [ ] **Ride booking (Uber / Ola)** — recipe + the new primitives it forces: location/maps
  handling, live/real-time state, pickup & drop selection, fare confirmation (sensitive →
  Phase 3 approval).
- [ ] **Messaging / comms (WhatsApp / Telegram)** — recipe + notification reading, open chat,
  compose/reply, send (sensitivity configurable per owner).
- [ ] **Recipe registry** — a community-contributable collection of app recipes (an OSS
  asset), with a contribution guide and validation: **every recipe must ship a golden flow**
  that runs in the eval harness, or it doesn't merge.
- [ ] **Keep expanding** — shopping, travel, bills, etc., each as a recipe.

## Explicitly out of scope
- Anything that genuinely needs a *core* change loops back to Phase 1 (a new perception/action
  primitive) or Phase 3 (a new class of sensitive action). That's expected occasionally — the
  test is that it's **additive**, not a rewrite.

## Exit criteria (measurable)
- [ ] **≥3 verticals** (food + rides + comms) working through recipes, in the eval harness.
- [ ] Adding the **4th vertical** needs only a recipe + a golden flow — no core changes.
- [ ] At least one **externally contributed recipe** lands and passes validation.

## Key risks & open questions
- Each vertical surfaces a new primitive (maps for rides, notifications for comms) — budget for
  some Phase-1 work each time; just keep it shared and additive.
- **Maps / live state** (rides) is materially harder to read than static lists — may stress the
  vision fallback.
- Recipe **drift**: apps change UIs constantly; recipes + golden flows must make breakage
  *visible* fast (that's exactly what the eval harness is for).
