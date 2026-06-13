# Phase 0 — Baseline ✅ (done)

**Goal:** Prove the core idea works at all — a real Android device, driven by an agent
through the semantic accessibility tree, end to end.

**Status:** Complete as of 2026-06-13.

## What exists

- **Local runtime** on Apple Silicon: a hand-built `vrski_dev` AVD (Android 34, Google
  Play, arm64) booting headless; uiautomator2 driving it; a FastAPI control server on
  `:7070`; an MCP server exposing ~23 tools. (Setup specifics live in the session memory
  `vrski-local-runtime`.)
- **Stage A proven live:** sideloaded Wikipedia (login-free) and drove
  launch → 4 onboarding pages → skip personalization → search → type → open article,
  entirely through the REST/MCP surface an agent uses. No mock mode.

## The six findings (the real value of Stage A)

What an agent actually sees underneath, discovered by driving a real app:

1. **Tap-by-text was ambiguous** — the action route returned the first match, so a search
   box echoing the query beat the suggestion row. ✅ **Fixed** (rank non-editable > clickable).
2. **`type` faked success** with no focused field (`adb input text` returns 0 regardless).
   ✅ **Fixed** (require a focused field; fail loudly + screenshot).
3. **The tree was ~70% noise** (empty containers, status bar, every keyboard key).
   ✅ **Fixed** (default `salient` filter, 122 → 34 elements; raw via `salient=false`).
4. **WebView / Compose content is invisible to the tree** — the article body and the
   Compose onboarding buttons exposed no usable nodes. ➡️ **Phase 1** (vision-backed fallback).
5. **`editable` flag false-positives** on focusable non-TextViews. ➡️ **Phase 1**.
6. **First-run apps are walls of interstitials** (onboarding, coachmarks, promos).
   ➡️ **Phase 1** (generic blocker handling + progress guard).

## Exit criteria — met

- [x] A real device boots and is drivable through the agent surface.
- [x] A multi-screen task completes end to end on a real app.
- [x] The top three reliability findings fixed and verified live.

➡️ Continue to [Phase 1 — Trustworthy Spine](./phase-1-trustworthy-spine.md).
