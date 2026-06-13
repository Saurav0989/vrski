# Vrski Roadmap

> **Built for agents. Not adapted for them.**

This is the long-haul plan for taking Vrski from "the spine works on one device" to
"the default way any AI agent touches Android." It is organized into phases. Each
phase has its own file with goal, scope, exit criteria, and risks. We work them one
at a time, prove each on a real device, and only mark things done off a live run.

---

## North star

A human grants their AI agent a real Android phone. The human logs into apps **once**;
from then on any agent — Hermes, Claude Code, OpenClaw, any MCP harness — can install
and operate **any** app to do real-world tasks (order food, book a ride, message a
friend) by reading the app's *meaning* (the accessibility tree, not pixels) and acting
on it — while the **human keeps the keys** to anything that spends money or can't be
undone.

## What we're optimizing for (decisions — 2026-06-13)

- **End game: open-source standard.** Vrski wins by becoming the default *self-hosted*
  runtime/spec that agent harnesses adopt — not a hosted SaaS. Hosting is explicitly
  parked (see the Appendix).
- **Trust is built early.** The owner-approval + audit layer (Phase 3) lands *before*
  the first real-money vertical (Phase 4). An agent must not be able to spend or take
  irreversible action without the owner's explicit yes.
- **Every vertical, via one playbook.** Start with food delivery (Swiggy / Zomato /
  Uber Eats), then ride booking (Uber / Ola), then messaging (WhatsApp / Telegram),
  then keep going. But each new vertical is a *recipe*, not a rewrite. The playbook is
  the adoption multiplier.
- **Long-haul & steady.** Depth over demo. Reliability is *measured* (an eval harness),
  not asserted. No shortcuts we'd have to undo.

## Design principles

1. **Semantic-first, vision-backed.** The accessibility tree is the primary interface;
   the screenshot is a *first-class* fallback for the screens where the tree is blind
   (WebView, Compose, games). We proved on day one that "never a pixel" is false — the
   moments that mattered most (opening and reading an article) needed vision.
2. **Honest signals over optimistic ones.** A tool must fail *loudly* when it didn't do
   the thing. We found `type` faking success with no focused field — that class of bug
   is the enemy. An agent that's been lied to makes confident wrong decisions.
3. **The human is the root of trust.** Logins, 2FA, payments, irreversible actions —
   these route to the owner, by design, forever.
4. **Recipes, not bespoke code.** Per-app and per-vertical knowledge lives in
   declarative, shareable recipes the community can contribute. That's how an OSS
   standard scales to "all the things."
5. **Measure reliability.** "Better and better" only means something if we can watch the
   success rate move. The eval harness is a deliverable, not an afterthought.

---

## Where we are — Phase 0 (done ✅)

- Local single-emulator runtime on Apple Silicon; semantic accessibility tree → JSON
  over MCP + REST.
- Stage A proven end-to-end on a real device: sideloaded Wikipedia, driven
  launch → onboarding → search → type → article entirely through the agent surface.
- Three reliability fixes shipped & verified live: tap-by-text disambiguation,
  type-requires-focus, and a salience filter (122 → 34 elements).
- Known gaps carried forward: WebView/Compose opacity, the `editable` false-positive,
  interstitial walls. See [`phase-0-baseline.md`](./phase-0-baseline.md).

## The phases at a glance

| # | Name | Goal | Retires the risk that… | Exit criteria (short) |
|---|------|------|------------------------|------------------------|
| 0 | Baseline ✅ | A real device, driven semantically | …the core idea doesn't work | Stage A passes live (done) |
| 1 | [Trustworthy Spine](./phase-1-trustworthy-spine.md) | Drive *any single app* reliably & honestly | …the read→act loop can't be trusted | Golden flows ≥90% on ≥4 login-free apps; eval harness green |
| 2 | [Identity & One-Time Login](./phase-2-identity-and-login.md) | Owner logs into any app once; agent reuses forever; walls hand back | …real apps are gated behind logins/2FA | Login once → operate across restarts; OTP/CAPTCHA handed back |
| 3 | [Trust, Control & Audit](./phase-3-trust-and-control.md) | Owner approves spend/irreversible actions; full audit | …an agent could spend/act without consent | Sensitive action blocked without owner OK; spend cap enforced; replayable audit |
| 4 | [Vertical 1 — Food Delivery](./phase-4-vertical-food-delivery.md) | Nail the flagship + ship the Vertical Playbook | …we can only do toy apps, each one bespoke | Food order to owner-approved payment, repeatable; playbook documented |
| 5 | [More Verticals](./phase-5-more-verticals.md) | Rides → Comms → expand, via the playbook | …adding a vertical needs core changes | ≥3 verticals via recipes only |
| 6 | [Concurrency & Scale](./phase-6-concurrency-scale.md) | Many isolated sessions on one host | …it's stuck at one agent, one phone | N concurrent isolated sessions, stable |
| 7 | [Adoption & Ecosystem](./phase-7-adoption-ecosystem.md) | Become the default harnesses reach for | …great tech that nobody adopts | A stranger runs a real task in minutes; ≥1 harness ships first-class support |

## How the phases depend on each other

- **Phase 1 is the foundation for everything** — an unreliable loop poisons every
  vertical, so it comes first.
- **Phases 2 and 3 are the gates** that make real tasks *possible* and *safe*. Both land
  before Phase 4: you can't order food without being logged in (2), and we won't touch a
  payment screen without the approval layer (3).
- **Phase 4 produces the playbook; Phase 5 is "apply the playbook."**
- **Phases 6 and 7** take Vrski from "works for you" to "works for the world" and can
  progress partly in parallel once 1–3 are solid.

```
        0 ──► 1 ──►┬──► 2 ──┐
                   │        ├──► 4 ──► 5
                   └──► 3 ──┘
                   1 ──────────────► 6
                   1..4 ───────────► 7
```

## How we work (the loop, every phase)

1. Open the phase file. 2. Pick the next work item. 3. Build it. 4. **Prove it on the
real emulator** and add it to the eval harness. 5. Commit on a branch. 6. Tick the
phase checklist and re-check exit criteria. We never mark a capability "done" off a
mock — only off a live run.

---

## Appendix — parked: hosted / managed Vrski

Deliberately **out of scope** given the open-source-standard choice. If we ever revisit,
it would need: a cloud device farm, a multi-tenant auth broker (the
"Google-2FA-needs-a-real-phone" problem at scale), a serious look at Play Store / app
Terms of Service and legal exposure, and billing. Parked, not planned — recorded here so
we don't accidentally drift into it.
