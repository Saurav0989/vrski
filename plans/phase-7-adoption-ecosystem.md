# Phase 7 — Adoption & Ecosystem (the win condition)

**Goal:** Make Vrski the **default** way agents touch Android.

**Why now / risk retired:** The end game is an open-source *standard*. Great tech that
nobody adopts loses. This phase turns a working runtime into something a stranger picks up,
trusts, and builds on — and that other harnesses ship support for. It can progress partly in
parallel once Phases 1–4 are solid (you need a *reliable* runtime before you market it).

**Depends on:** A solid Phase 1–4 (you can't sell an unreliable runtime).

---

## Scope
- [ ] **Killer onboarding.** One-command setup; the human's first five minutes are flawless
  (the hardest, most-abandoned moment). A great docs site + quickstart.
- [ ] **First-class harness integrations** — a **Hermes skill/plugin**, clean **Claude Code**
  MCP packaging, **OpenClaw**, each with copy-paste setup and a worked example.
- [ ] **The recipe registry as a flywheel** — make contributing an app recipe easy and
  rewarding; publish a clear **spec** so others can implement/extend Vrski.
- [ ] **Reference demos / videos**, and **outreach** to the Nous/Hermes community and beyond.
- [ ] **Project hygiene for adopters** — versioning, stability guarantees, a contribution &
  governance baseline, and an honest "what works / what doesn't yet" page.

## Explicitly out of scope
- Hosting it for people (parked). Adoption here means *they* run Vrski easily, not that we run
  it for them.

## Exit criteria (measurable)
- [ ] Someone who **isn't you** installs Vrski and completes a **real task in < a few minutes**
  from a clean machine, following only the docs.
- [ ] **≥1 harness ships first-class Vrski support** (or a maintained community plugin exists).
- [ ] **Community recipes start landing** in the registry and passing validation.

## Key risks & open questions
- **Docs/onboarding rot** — the setup is the product here; it must stay effortless as the code
  moves.
- **Supporting many harnesses** is real maintenance cost — keep the core MCP surface clean so
  most integration is config, not code.
- **Abuse / ToS as usage grows** — be ready with clear guidance on acceptable use, and lean on
  the Phase 3 trust layer as the responsible-by-default story.
