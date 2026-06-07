# Vrski — Setup Guide

> **Give your Hermes agent a real Android phone.**
> The owner signs into Google **once**. After that, the agent installs apps,
> orders food, books rides, and sends messages on the owner's behalf — all
> through MCP tool calls, no screenshots, no vision model.

This guide is the fastest path from zero to a working setup. It has two parts:

1. **You (the human)** do a one-time setup and sign into Google.
2. **Your Hermes agent** wires itself to Vrski and takes over.

For deeper detail, see [`README.md`](./README.md) (full architecture + tool
reference) and [`VRSKIAGENT.md`](./VRSKIAGENT.md) (the agent's own instructions).

---

## Why a human signs in once

An agent can do almost everything on the phone — except the very first Google
sign-in. Google guards new sign-ins with **2-Step Verification** (a "tap this
number on your phone" prompt) that only your physical phone can approve.

So you sign in **one time**. The account then lives on the emulator, and your
agent uses it from then on. You never sign in again unless the account is
deliberately signed out.

---

## Part 1 — Human setup (one time, ~10 minutes)

### Prerequisites

- macOS (Apple Silicon) or Linux
- [Hermes agent](https://github.com/NousResearch/hermes-agent) already installed
  (`hermes setup` has been run, so `~/.hermes` exists)
- A Google account you want the agent to use
- Homebrew (macOS) for the Android SDK

### Step 1 — Clone Vrski into your Hermes folder

`~/.hermes` already exists from `hermes setup`. Clone Vrski inside it:

```bash
cd ~/.hermes
git clone https://github.com/Saurav0989/vrski.git
cd vrski
```

### Step 2 — Install prerequisites

```bash
# Android SDK: platform-tools + emulator + a Play-Store system image
brew install --cask android-commandlinetools

# Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Step 3 — Create the emulator (once)

```bash
bash scripts/setup_avd.sh
```

This creates the `vrski_dev` Android Virtual Device.

### Step 4 — Sign into Google (the one human step)

```bash
bash scripts/login.sh
```

The emulator opens **with its window visible** and lands on the Play Store
sign-in screen. In that window:

1. Tap **Sign in**, enter your Google **email** and **password**.
2. When Google says **"Verify it's you,"** approve the prompt on your **real
   phone** (tap the matching number).
3. Accept any terms until you reach the **Play Store home screen**.

Then return to the terminal and press **Enter**. The script confirms the
account, saves a snapshot, and offers to close the emulator. **Say yes — you're
done.**

### Step 5 — Hand off to your Hermes agent

Open your Hermes agent and say:

> **"I've signed into Vrski. Wire yourself up to it."**
> — and tag the file **`@VRSKIAGENT.md`**

That's it. You're out of the loop now.

---

## Part 2 — What your Hermes agent does

When you tag [`VRSKIAGENT.md`](./VRSKIAGENT.md), the agent reads it and:

1. Starts Vrski:
   ```bash
   cd ~/.hermes/vrski
   bash scripts/start_vrski.sh
   ```
2. Registers the MCP server:
   ```bash
   claude mcp add vrski python -m vrski.mcp.server
   # or adds it to its MCP config (Hermes / OpenClaw)
   ```
3. Confirms the device is ready (`vrski_check_setup` → `ready: true`).
4. Starts doing what you ask: *"install WhatsApp," "order my usual," "reply to
   the latest message."*

The agent reads the screen as structured JSON and acts by element — it never
guesses pixels and never needs a vision model.

---

## After setup — just talk to your agent

You never touch the emulator again. Ask your Hermes agent in plain language:

- *"Install Instagram and open it."*
- *"Order a large pepperoni from the food app."*
- *"Book a ride home."*
- *"Send a WhatsApp to Mom saying I'll be late."*

The agent handles the taps and typing through Vrski.

---

## If something goes wrong

| Symptom | Fix |
|---------|-----|
| Agent says Vrski tools aren't responding | Run `bash scripts/start_vrski.sh` in `~/.hermes/vrski` |
| Agent says the Google account is signed out | Run `bash scripts/login.sh` again to sign back in |
| Emulator is stuck or acting weird | Run `bash scripts/reset_session.sh` (keeps your Google login) |
| An app shows its own login wall | Sign into that app once in the emulator window, same as Google |

---

## Learn more

- **[`README.md`](./README.md)** — full architecture, all MCP tools and their
  return shapes, the REST API, and integration paths for any harness.
- **[`VRSKIAGENT.md`](./VRSKIAGENT.md)** — the exact instructions your agent
  follows: the read→act loop, golden rules, and recovery steps.

---

**One line:** sign into Google once with `scripts/login.sh`, tag
`@VRSKIAGENT.md`, and let your Hermes agent run your phone.
