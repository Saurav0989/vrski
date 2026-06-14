# Hard Mode — Adversarial Apps & the Real-Device Track

> Some apps are built to keep automation out. Vrski's stance: **detect and hand back; never evade.**

Most of Android is the **long tail** — apps with no API that don't fight automation
(messaging, calendar, notes, information, settings, the owner's own accounts). Vrski
operates those reliably through the accessibility tree; that is the main product (see the
recipes in `vrski/recipes.py`).

A minority of apps — **food delivery, ride-hailing, banking**, and similar transactional
apps — actively resist automation. This file documents that "hard mode" honestly.

## What we found (Phase 2, on a real run)

Driving real commercial apps on the emulator:

- **Grubhub:** install + launch + "Continue with Google" SSO all worked — then the app's
  **PerimeterX anti-bot** check threw a *"prove you're not a robot"* CAPTCHA
  (`PXBlockActivity`) the instant it had an authenticated session.
- **Uber Eats / DoorDash:** wouldn't even install — Google Play reported *"your device
  isn't compatible with this version"* (device-integrity / emulator rejection).

The lesson: **the UI-automation layer is not the blocker.** It works great. The blocker is
**anti-bot and device-integrity detection** — and no amount of better tapping changes that.

## Our stance: detect, don't evade

Vrski **will not**:
- solve or bypass CAPTCHAs,
- spoof device integrity / Play Integrity / SafetyNet,
- fingerprint-spoof to imitate a human session,
- or otherwise defeat an app's anti-automation controls.

That arms race is unwinnable, usually violates the app's Terms of Service, and is not who we
are. Staying clean is also what lets Vrski become a **standard** rather than a gray-area
tool. So when Vrski hits such a wall, it **detects it and hands back to the human**:

- `vrski_check_wall` classifies the screen as `bot_block` / `otp` / `2fa` / `login` and flags
  `human_required`.
- On a human-only wall the agent stops and surfaces it to the owner (with a screenshot) — it
  does not try to get past it.

## What hard mode actually needs

For an owner who genuinely wants to use a transactional app through their agent:

1. **A real device (Phase 6).** Real Android hardware passes the "device not compatible" /
   Play Integrity checks the emulator fails. Vrski drives a real device over ADB through the
   exact same tools.
2. **Human-in-the-loop at the walls (Phase 3).** Even on real hardware, some apps will throw
   a CAPTCHA or OTP. The owner clears those; the agent does the rest, and any sensitive action
   (pay / place order) is gated behind owner approval regardless.
3. **Acceptance that some apps stay closed.** A few apps will block automation even on a real
   device. That is a documented boundary, not a target. We don't fight it.

## Where we draw the line

| Situation | Vrski does |
|-----------|-----------|
| App has no API, doesn't fight automation | Operate it fully (the long tail — the main product) |
| Login offers "Continue with Google" | Complete it with the device account |
| App throws OTP / 2FA / "verify it's you" | Hand back to the owner |
| App throws a CAPTCHA / anti-bot block | Hand back to the owner; never solve it |
| App rejects the device (integrity) | Needs a real device (Phase 6); if it still blocks, leave it |

The honest summary: **Vrski is excellent where automation is legitimate, and a polite guest
everywhere else.**
