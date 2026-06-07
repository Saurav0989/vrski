# VRSKIAGENT — How an AI Agent Uses Vrski

> **You are an AI agent (Hermes, Claude Code, OpenClaw, …). This file tells you how to control a real Android phone for your owner through Vrski.**

Your owner has tagged this file because they finished the one-time setup: they cloned Vrski and signed a Google account into the emulator by hand. **That part is done. Do not try to redo it.** Your job starts now.

---

## What Vrski gives you

Vrski is an MCP server that exposes a real Android emulator as **tool calls**. You read the screen as structured JSON (the accessibility tree) and act on it by element text or ID — no screenshots, no vision model, no pixel guessing.

```
You call  vrski_get_screen()      → JSON list of on-screen elements
You call  vrski_tap(text="Log in") → Vrski finds it and taps it
You call  vrski_type(text="...")   → types into the focused field
```

The emulator already has your owner's Google account signed in, so the Play Store works and you can install and use any app that has a normal login.

---

## Step 1 — Wire yourself up (do this once per machine)

The owner ran the sign-in script and is now talking to you. Bring Vrski online:

```bash
# From the repo your owner cloned (usually ~/.hermes/vrski)
cd ~/.hermes/vrski

# Start the emulator + Vrski control API (boots from the logged-in state)
bash scripts/start_vrski.sh
```

Then register the MCP server with your harness:

```bash
# Claude Code:
claude mcp add vrski python -m vrski.mcp.server

# Hermes / any MCP harness — add to your MCP config:
#   { "mcpServers": { "vrski": { "command": "python", "args": ["-m", "vrski.mcp.server"] } } }
```

Confirm you are connected and the account is live:

```
vrski_start_session("owner")
vrski_check_setup("owner")     → expect { "ready": true, "signed_in": true, "active_account": "...@gmail.com" }
```

If `ready` is true, you are fully wired. Proceed.

---

## Step 2 — The core loop

Every task is the same rhythm. **Never act blind — always read first.**

```
1. vrski_get_screen(session_id)        # see what's actually on screen
2. decide which element to act on       # by its text / id / content_desc
3. vrski_tap / vrski_type / vrski_swipe # do one action
4. go back to 1                          # confirm the result, then continue
```

After an action that changes screens, use `vrski_wait_for_element(...)` on something you expect next, instead of guessing with a fixed delay.

---

## Step 3 — Do what your owner asked

Examples of real tasks and how they decompose:

**"Install WhatsApp"**
```
vrski_install_app("owner", "com.whatsapp")     # handles Play Store search + Install
vrski_wait_for_element("owner", text="Open")    # or check vrski_is_installed
```

**"Order my usual from the food app"**
```
vrski_launch_app("owner", "<food app package>")
vrski_get_screen("owner")                        # read the home screen
vrski_dismiss_popups("owner")                    # clear any welcome dialogs
vrski_tap("owner", text="Search")
vrski_type("owner", text="...")
# ...keep reading + tapping through the flow...
```

**"Reply to the latest message"**
```
vrski_launch_app("owner", "<messaging app>")
vrski_get_screen("owner")                        # find the chat
vrski_tap("owner", text="<contact name>")
vrski_tap("owner", content_desc="Message")
vrski_type("owner", text="...")
vrski_tap("owner", content_desc="Send")
```

---

## Golden rules

1. **Read before every action.** Call `vrski_get_screen` first. The screen changes between steps; never assume.
2. **Prefer text over coordinates.** `vrski_tap(text="Next")` survives layout changes. Raw `x,y` is a last resort.
3. **A failed tap is data, not a crash.** It returns `{ "success": false, "error": "...", "screenshot_base64": "..." }`. Read it, decide, retry differently.
4. **Dismiss popups when stuck.** If an expected element isn't there after 2–3 reads, call `vrski_dismiss_popups` and look again.
5. **Never try to sign into Google yourself.** Google's 2-Step Verification can only be approved by the owner's physical phone. If you find the device signed out (`vrski_check_setup` → `signed_in: false`), **stop and tell the owner**: *"The Google account is signed out. Please run `bash scripts/login.sh` again to sign back in."*
6. **CAPTCHA / human verification = ask the owner.** If you hit a CAPTCHA or "verify it's you" wall inside any app, surface it. Do not attempt to solve it.
7. **One session per owner.** Reuse the same `session_id`. End it with `vrski_end_session` only when the work is fully done.

---

## Tool quick reference

| Tool | Purpose |
|------|---------|
| `vrski_start_session(session_id)` | Begin / attach a session |
| `vrski_check_setup(session_id)` | Is the device ready & signed in? |
| `vrski_get_screen(session_id)` | Read on-screen elements as JSON |
| `vrski_wait_for_element(session_id, text=…)` | Block until an element appears |
| `vrski_tap(session_id, text=… / element_id=… / content_desc=…)` | Tap an element |
| `vrski_type(session_id, text=…)` | Type into the focused field |
| `vrski_swipe(session_id, direction=…)` / `vrski_scroll_to(session_id, text=…)` | Scroll |
| `vrski_back / vrski_home / vrski_recent_apps(session_id)` | Hardware keys |
| `vrski_install_app / vrski_launch_app / vrski_close_app / vrski_uninstall_app(session_id, package_name)` | App lifecycle |
| `vrski_is_installed / vrski_list_installed(session_id)` | Query apps |
| `vrski_dismiss_popups(session_id)` | Clear blocking dialogs |
| `vrski_get_playstore_account(session_id)` | Which Google account is active |

Full signatures and return shapes: see `README.md`.

---

## When something breaks

| Symptom | What to do |
|---------|-----------|
| `vrski_*` calls all fail / connection error | The API/emulator isn't running. Run `bash scripts/start_vrski.sh`. |
| `vrski_check_setup` → `signed_in: false` | Account signed out. Ask the owner to run `bash scripts/login.sh`. |
| App shows a login wall you can't pass | Tell the owner; they sign into that app the same way (once). |
| Emulator stuck / weird state | `bash scripts/reset_session.sh` (this wipes app state, not the Google login). |
| Element not found repeatedly | `vrski_dismiss_popups`, then `vrski_get_screen` again; the UI may have shifted. |

---

**In one line:** the owner signed in once; you drive the phone from here — read the screen, act by element, ask the owner only when a human-only wall (Google 2FA, CAPTCHA, an app's own login) blocks you.
