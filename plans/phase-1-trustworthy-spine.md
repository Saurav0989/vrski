# Phase 1 — The Trustworthy Spine

**Goal:** Make the read → act → verify loop reliable and *honest* on any single app, and
make reliability **measurable**.

**Why now / risk retired:** Everything downstream (logins, payments, every vertical)
compounds on this loop. Stage A showed it's ~80% there — but the failure modes (blind on
WebView/Compose, false-success, noisy tree) would silently sink real tasks. An unreliable
spine poisons every phase above it.

**Depends on:** Phase 0.

---

## Scope

### Perception (semantic-first, vision-backed)
- [ ] **Vision fallback as first-class.** Auto-attach a screenshot when the salient tree
  is empty/low-signal or a tap is ambiguous. Add a `vrski_look()` that returns the
  screenshot + salient tree together, so the agent's own model can reason about screens
  the tree can't describe. (Vrski stays model-agnostic — we hand over pixels, the harness's
  VLM interprets.)
- [ ] **WebView handling.** Detect WebViews; enable/extract their accessibility text where
  possible; otherwise fall back to vision for content bodies (the Alan-Turing-article problem).
- [ ] **Label-less Compose elements.** A "tap by visual label" path for clickable `View`s
  with no text/id (the onboarding "Forward" / opaque-View problem) using the vision fallback.
- [ ] **Fix the `editable` false-positive** (finding #5) — focusable non-TextViews wrongly
  flagged editable.

### Action robustness
- [ ] **`wait_for_stable_screen`** primitive — the screen settles before/after an action,
  replacing fixed sleeps.
- [ ] **Progress guard** — detect "the screen didn't change after my action" and surface it
  so agents stop looping (the suggestion-tap loop we hit).
- [ ] **Generic blocker handling** (finding #6) — a robust `dismiss_blockers` covering
  onboarding pages, coachmarks, promos, permission dialogs, "rate this app," update prompts,
  with a safe allow/deny policy.
- [ ] **Standardize retry + reconnect** (already partly present) into one predictable layer.

### Element model
- [ ] **Stable element handles** so an agent can refer to "that element" across reads.
- [ ] **Parent-clickable resolution** — when the labelled node isn't itself clickable, tap
  the right ancestor / use bounds fallback.

### Honesty / positioning
- [ ] **Reframe README & docs** to "semantic-first, vision-backed" (drop "no screenshots,
  ever"). Document the real failure modes openly — honesty is a feature for an OSS standard.

### The Eval Harness (pillar — the regression net for the whole journey)
- [ ] A suite of **scripted real-app tasks** on login-free apps (Wikipedia, F-Droid, a
  browser, a couple of open apps) that report pass/fail + step count + failure reason,
  runnable against the emulator.
- [ ] Track success-rate **over time** so "better and better" is visible. Every later phase
  adds its golden flows here.

## Explicitly out of scope
- Logged-in apps (Phase 2), payments / approval (Phase 3), multiple verticals (Phase 4+).

## Exit criteria (measurable)
- [ ] A defined set of **golden flows across ≥4 login-free apps pass ≥90%** over repeated
  runs in the eval harness.
- [ ] **No silent-success bugs** remain in tap/type/scroll — every action verifies its effect.
- [ ] WebView/Compose screens are at least **navigable via the vision-backed fallback**.

## Key risks & open questions
- **Vision approach:** default is to return the screenshot and let the harness's own model
  reason (keeps Vrski model-agnostic). *Open:* do we add lightweight on-device OCR for plain
  text extraction, or stay pure pass-through?
- **WebView a11y** is inconsistent across apps — may need per-app fallback hints (which
  becomes recipe data in Phase 4).
- Risk of over-filtering in `salient` mode hiding a needed element — keep `salient=false`
  and good telemetry on what got dropped.
