# Vrski — Agent-Native Android Runtime

> **Built for agents. Not adapted for them.**

Vrski gives AI agents programmatic access to a real Android device through tool calls. It is **semantic-first, vision-backed**.

**Semantic-first:** every app on Android exposes its UI as an accessibility tree — a structured hierarchy of elements with types, labels, resource IDs, bounds, and interaction flags. Vrski intercepts that tree and hands it to your agent as clean JSON, so the agent reads *meaning*, not pixels — no vision model needed for the vast majority of screens.

**Vision-backed:** some screens don't describe themselves in the tree — WebView content (article/page bodies), parts of Compose/Flutter UIs, and games expose little or nothing. On those, Vrski automatically attaches a screenshot and flags the screen (`low_signal` / `has_webview`) so the agent can fall back to looking and tap by coordinates. Semantic when it can, visual when it must.

```
Agent calls vrski_get_screen()
→ gets { type: "Button", text: "Log In", id: "com.app:id/login_btn", clickable: true }
→ calls vrski_tap(text="Log In")
→ Vrski resolves coordinates internally, taps, confirms
→ Agent acts on meaning — pixels only when the tree can't describe the screen
```

---

## 📚 Documentation — start here

| Read this | If you are… |
|-----------|-------------|
| **[`GUIDE.md`](./GUIDE.md)** | A human setting up Vrski for the first time. Clone → sign in once → hand off to your agent. **Start here.** |
| **[`VRSKIAGENT.md`](./VRSKIAGENT.md)** | An AI agent (Hermes / Claude Code / OpenClaw). How to wire in and drive the phone. The owner tags this for you. |
| **`README.md`** (this file) | A developer who wants the full picture — architecture, every MCP tool, the REST API, and integration paths. |

---

## Why This Matters for Agent Harnesses

| Capability | Vision-based (screenshots) | Vrski (semantic) |
|-----------|--------------------------|-----------------|
| Read UI | Vision model interprets pixels | Direct JSON from accessibility API |
| Tap accuracy | Coordinate-based, breaks on layout changes | Text / ID / desc — always finds the right target |
| Speed | Screenshot → vision call → decision | UI tree → decision, no vision API |
| Cost | Vision API call every action | Vision only as a fallback, not every action |
| Reliability | Hallucinations, wrong taps | Deterministic where the tree describes the screen; screenshot fallback where it doesn't |
| Parallelism | One stream | Multiple sessions, unlimited agents |
| Audit trail | Screenshots (large, ambiguous) | Structured JSON log of every action |

Vrski is the correct interface for agents operating on Android. It is what accessibility tools use, and agents are accessibility tools — with a screenshot fallback for the screens accessibility can't reach.

---

## Architecture

```
┌─────────────────────────────────────────┐
│        AI Agent / Harness               │
│  (Claude Code / Hermes / OpenClaw / …)  │
└──────────────────┬──────────────────────┘
                   │ MCP tool calls  ─OR─  HTTP REST
┌──────────────────▼──────────────────────┐
│         Vrski MCP Server                │
│         vrski/mcp/server.py             │
│         (FastMCP, 23 tools)             │
└──────────────────┬──────────────────────┘
                   │ httpx  →  localhost:7070
┌──────────────────▼──────────────────────┐
│       Vrski Control API (FastAPI)        │
│       vrski/api/main.py  :7070          │
│  /session  /screen  /action  /install   │
│  /auth/playstore  /dismiss_popups       │
│  /setup  /setup/status                  │
└────────────┬───────────────┬────────────┘
             │ uiautomator2  │ ADB subprocess
┌────────────▼───────┐  ┌───▼──────────────────┐
│  Semantic UI Layer  │  │  ADB Control Layer    │
│  XML tree → JSON   │  │  install · key events │
│  find · tap · type │  │  pm list · force-stop │
└────────────┬───────┘  └───┬──────────────────┘
             └──────┬───────┘
┌────────────────────▼────────────────────┐
│     Android Emulator (AVD)              │
│     API 34 · arm64-v8a · Google Play    │
│     4 GB RAM · 6 GB storage             │
└─────────────────────────────────────────┘
```

---

## Requirements

- macOS Apple Silicon (M1/M2/M3/M4) — arm64 emulator images
- Python 3.11+
- Android SDK — `platform-tools`, `emulator`, `system-images;android-34;google_apis_playstore;arm64-v8a`
- A dedicated Gmail account for Play Store automation (do **not** use a personal account)

Install Android SDK tools via Homebrew:
```bash
brew install --cask android-commandlinetools
```

---

## Setup — for the human (one time)

The human owner does this **once**. After it, the AI agent runs everything on its own.

> **Why does a human sign in?** Google guards every new sign-in with 2-Step
> Verification — a "tap 35 on your phone" prompt that only the owner's real
> phone can approve. No agent can pass that. So the human signs in one time;
> the account then lives on the emulator and the agent uses it forever.

### 1. Clone the repo into your Hermes folder

`~/.hermes` already exists — it was created automatically when you ran
`hermes setup` ([Hermes agent](https://github.com/NousResearch/hermes-agent)).
Just clone Vrski inside it:

```bash
cd ~/.hermes
git clone https://github.com/Saurav0989/vrski.git
cd vrski
```

### 2. Install prerequisites

```bash
# Android SDK (platform-tools + emulator + a Play-Store system image)
brew install --cask android-commandlinetools

# Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3. Create the emulator (once)

```bash
bash scripts/setup_avd.sh
```

Installs the system image and creates the `vrski_dev` AVD.

### 4. Sign in to Google (the one human step)

```bash
bash scripts/login.sh
```

This boots the emulator **with its window visible**, opens the Play Store
sign-in screen, and waits. In the emulator window:

1. Tap **Sign in**, enter your Google email and password.
2. Approve the **"verify it's you"** prompt on your real phone.
3. Accept any terms until you reach the Play Store home screen.

Then return to the terminal and press **Enter**. The script confirms the
account, saves a logged-in snapshot, and offers to close the emulator. **Say
yes — you're done.** You never need to do this again.

### 5. Hand off to your agent

Go to your Hermes agent (or Claude Code, OpenClaw, …) and say:

> *"I've signed into Vrski. Wire yourself up to it."* — and tag **`@VRSKIAGENT.md`**

[`VRSKIAGENT.md`](./VRSKIAGENT.md) tells the agent how to start Vrski and drive
the phone. From here on, the agent does the rest. **You're out of the loop.**

---

## Integrating with Agent Harnesses

### Path A — MCP (preferred for Claude Code, Hermes, OpenClaw)

Vrski exposes all tools via the Model Context Protocol. Any harness that supports MCP gets the full tool set immediately.

**Claude Code:**
```bash
claude mcp add vrski python -m vrski.mcp.server
```

Or add to your `claude_mcp_config.json` / project `.mcp.json`:
```json
{
  "mcpServers": {
    "vrski": {
      "command": "python",
      "args": ["-m", "vrski.mcp.server"],
      "env": {
        "VRSKI_API_URL": "http://localhost:7070"
      }
    }
  }
}
```

A ready-to-use config is at `vrski_mcp_config.json` in this repo.

**Hermes / any MCP-capable harness:**
```json
{
  "mcpServers": {
    "vrski": {
      "command": "python",
      "args": ["-m", "vrski.mcp.server"]
    }
  }
}
```

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `VRSKI_API_URL` | `http://localhost:7070` | FastAPI server URL (MCP server reads this) |
| `VRSKI_EMULATOR_SERIAL` | `emulator-5554` | ADB device serial |
| `VRSKI_MOCK` | `0` | Set to `1` to run without a real device (for CI) |
| `VRSKI_SIMULATE` | `false` | Session-level mock — API starts but no real ADB calls |

---

### First-Run Onboarding (human signs in once, agent runs forever)

The Google sign-in is the **one** thing an agent cannot do — Google's 2-Step
Verification requires the owner's physical phone. So the responsibility splits
cleanly:

| Step | Who | How |
|------|-----|-----|
| Clone repo, install deps, create AVD | Human | `git clone` + `setup_avd.sh` |
| **Sign into Google** | **Human (once)** | `bash scripts/login.sh` |
| Start Vrski, drive the phone, use apps | **Agent (always)** | `start_vrski.sh` + MCP tools |

**The agent's contract — every session:**
1. `vrski_start_session(session_id)`
2. `vrski_check_setup(session_id)` →
   - `ready: true` → proceed with the owner's task.
   - `signed_in: false` → **do not attempt to log in.** Tell the owner:
     *"The Google account is signed out — please run `bash scripts/login.sh` again."*

The agent never asks for or stores a password. The account already lives on the
emulator from the human's one-time sign-in. Full agent instructions:
[`VRSKIAGENT.md`](./VRSKIAGENT.md).

> **Optional accelerator:** `vrski_setup(session_id, email, password)` and
> `vrski_signin_playstore(session_id)` can auto-fill the email and password on
> the sign-in screen, but they still stop at Google's 2FA wall — the owner must
> approve on their phone. For most setups, `scripts/login.sh` (human-driven) is
> simpler and more reliable. Credentials, if used, are stored only in `.env`
> (git-ignored, never leaves the machine).

---

### Path B — REST API (for harnesses without MCP)

The FastAPI server at `:7070` is the underlying interface. Build a thin plugin for your harness that wraps it:

```python
import httpx

class VrskiPlugin:
    def __init__(self, base="http://localhost:7070"):
        self.base = base
        self._session_id = None

    def start(self, session_id: str):
        r = httpx.post(f"{self.base}/session/start", json={"session_id": session_id})
        self._session_id = session_id
        return r.json()

    def get_screen(self) -> dict:
        return httpx.get(f"{self.base}/session/{self._session_id}/screen").json()

    def tap(self, text: str = None, element_id: str = None) -> dict:
        return httpx.post(f"{self.base}/session/{self._session_id}/action",
                          json={"type": "tap", "text": text, "element_id": element_id}).json()

    def type(self, text: str) -> dict:
        return httpx.post(f"{self.base}/session/{self._session_id}/action",
                          json={"type": "type", "text": text}).json()

    def install(self, package_name: str) -> dict:
        return httpx.post(f"{self.base}/session/{self._session_id}/install",
                          json={"package_name": package_name}, timeout=360).json()
```

---

## MCP Tool Reference

All tools follow the same contract: they return a dict with `"success": true/false`. On failure they include `"error"` (string) and `"screenshot_base64"` (PNG, base64) so the agent can reason about why something failed.

### Session

```python
vrski_start_session(session_id: str)
# → { "session_id", "status": "ready", "emulator_serial" }

vrski_end_session(session_id: str)
# → { "status": "ended" }

vrski_get_session_status(session_id: str)
# → { "session_id", "status": "ready|busy|error", "current_app", "current_activity" }
```

### Screen

```python
vrski_get_screen(session_id: str, include_screenshot: bool = False, salient: bool = True)
# Returns only agent-relevant elements by default (drops empty layout containers,
# the system status bar, and soft-keyboard keys). Pass salient=False for the raw tree.
# A screenshot is auto-attached when the tree can't describe the screen.
# → {
#     "elements": [{ "id", "type", "text", "content_desc",
#                    "clickable", "scrollable", "editable",
#                    "bounds": { "left","top","right","bottom" } }],
#     "element_count": int,        # after the salient filter
#     "raw_element_count": int,    # before filtering
#     "salient": bool,
#     "has_webview": bool,         # content likely NOT in the tree — look instead
#     "low_signal": bool,          # too few readable elements — look instead
#     "vision_hint": str | None,   # set when you should reason from the screenshot
#     "package": str,
#     "activity": str,
#     "screenshot_base64": str | None
#   }

vrski_look(session_id: str)
# The vision-backed view: salient tree + a screenshot, together. Use on WebView /
# Compose / game screens, or when get_screen returns has_webview/low_signal.

vrski_wait_for_element(session_id: str, text: str = None, element_id: str = None, timeout: int = 15)
# → { "found": bool, "element": UIElement | None }

vrski_wait_stable(session_id: str, timeout: int = 10, settle_ms: int = 500)
# Wait until the screen stops changing (two identical UI dumps). Use after launching
# an app or triggering a transition, instead of a fixed sleep.
# → { "stable": bool, "elapsed_s": float, "polls": int }
```

**Tap & type now report progress.** `vrski_tap` returns `matched_count` and
`ambiguous` (when a label matches several elements it picks the actionable target,
not an input field that merely echoes the text), and both `vrski_tap` and
`vrski_type` return `screen_changed: bool` so you can detect a no-op and avoid
looping. `vrski_type` fails loudly (`success: false` + screenshot) if no input field
is focused — it will not silently type into nothing.

**Agent guidance:** always call `vrski_get_screen` before deciding what to tap. Never assume what's on screen.

### Actions

```python
vrski_tap(session_id, text=None, element_id=None, content_desc=None, x=None, y=None)
# Prefer text > element_id > content_desc. Use x/y only as absolute last resort.
# → { "success", "matched_element": str | None, "error"?, "screenshot_base64"? }

vrski_type(session_id, text: str, clear_first: bool = True)
# Types into whatever field is currently focused.
# → { "success" }

vrski_swipe(session_id, direction: "up"|"down"|"left"|"right", distance: int = 500, speed: int = 300)
vrski_scroll_to(session_id, text: str, max_swipes: int = 10)
# → { "success", "found": bool }

vrski_back(session_id)
vrski_home(session_id)
vrski_recent_apps(session_id)
# → { "success" }
```

**On failure:** `vrski_tap` returns `{ "success": false, "error": "Element not found: ...", "screenshot_base64": "..." }` with HTTP 200 — never HTTP 404. The agent should inspect the screenshot and retry or navigate differently.

### App Management

```python
vrski_install_app(session_id, package_name: str)
# Navigates Play Store, searches, taps Install, polls pm list packages until confirmed.
# Timeout: 300 seconds. Returns duration.
# → { "success", "package_name", "duration_seconds", "error" | None }

vrski_launch_app(session_id, package_name: str)
vrski_close_app(session_id, package_name: str)
vrski_uninstall_app(session_id, package_name: str)
vrski_is_installed(session_id, package_name: str)   # → { "installed": bool }
vrski_list_installed(session_id)                     # → { "packages": [str] }
```

### Play Store Auth

```python
vrski_signin_playstore(session_id, gmail: str, password: str)
# Full automated sign-in flow: launch Play Store → enter email → enter password
# → handle post-auth screens → confirm search bar visible.
# Returns captcha_detected if a CAPTCHA is shown — surface to human to complete once.
# → { "success", "account": str | None, "error": str | None }

vrski_get_playstore_account(session_id)
# → { "signed_in": bool, "account": str | None }
```

**Important:** Use a dedicated Gmail account for Vrski automation. Do **not** use a personal account.

### Setup & Credential Management

```python
# --- First run: call this once ---
vrski_setup(session_id, email: str, password: str)
# Saves credentials to .env, then signs into Play Store automatically.
# → { "success", "account", "already_signed_in", "message" }

# --- Every subsequent run ---
vrski_check_setup(session_id)
# → {
#     "ready": bool,            # true = credentials saved + device authenticated
#     "has_credentials": bool,  # true = email/password stored in .env
#     "saved_email": str|None,
#     "signed_in": bool,        # live sign-in state on device
#     "active_account": str|None,
#     "next_step": str|None     # human-readable instruction if not ready
#   }

vrski_signin_playstore(session_id, gmail=None, password=None)
# Signs in using saved credentials from .env (default) or explicit override.
# → { "success", "account": str | None, "error": str | None }

vrski_get_playstore_account(session_id)
# → { "signed_in": bool, "account": str | None }
```

### Popup Dismisser

```python
vrski_dismiss_popups(session_id)
# Scans the current screen for blocking dialogs and dismisses them:
# permission requests, Play Store update prompts, "App not responding",
# "Rate this app", "Not now", etc.
# Call this before any action if you suspect a dialog is blocking.
# → { "success", "dismissed": bool }
```

---

## REST API Reference

The FastAPI server (`localhost:7070`) is what the MCP server talks to internally. You can also hit it directly with curl during development.

```
POST  /session/start                       { "session_id": str }
POST  /session/{id}/end
GET   /session/{id}/status
GET   /session/{id}/screen                 ?include_screenshot=false
POST  /session/{id}/wait                   { "text"?, "element_id"?, "timeout": 15 }
POST  /session/{id}/action                 (see action shapes below)
POST  /session/{id}/install                { "package_name": str }
POST  /session/{id}/launch                 { "package_name": str }
POST  /session/{id}/close                  { "package_name": str }
POST  /session/{id}/uninstall              { "package_name": str }
GET   /session/{id}/apps                   → { "packages": [str] }
GET   /session/{id}/apps/{package_name}    → { "installed": bool }
POST  /session/{id}/auth/playstore         { "gmail"?: str, "password"?: str }   (omit → reads .env)
GET   /session/{id}/auth/playstore         → { "signed_in": bool, "account": str | None }
POST  /session/{id}/dismiss_popups
POST  /setup                               { "session_id": str, "email": str, "password": str }
GET   /setup/status                        ?session_id=...  → { "ready", "has_credentials", ... }
```

**Action body shapes:**
```json
{ "type": "tap",       "text": "Log In" }
{ "type": "tap",       "element_id": "com.app:id/login_btn" }
{ "type": "tap",       "content_desc": "Search" }
{ "type": "tap",       "x": 540, "y": 960 }
{ "type": "type",      "text": "hello@gmail.com", "clear_first": true }
{ "type": "swipe",     "direction": "up", "distance": 500, "speed": 300 }
{ "type": "scroll_to", "text": "Privacy Policy" }
{ "type": "back" }
{ "type": "home" }
{ "type": "recent_apps" }
```

**Curl examples:**
```bash
# Start session
curl -X POST localhost:7070/session/start \
  -H "Content-Type: application/json" -d '{"session_id": "s1"}'

# Get screen
curl localhost:7070/session/s1/screen

# Tap by text
curl -X POST localhost:7070/session/s1/action \
  -H "Content-Type: application/json" -d '{"type": "tap", "text": "Settings"}'

# Install WhatsApp
curl -X POST localhost:7070/session/s1/install \
  -H "Content-Type: application/json" -d '{"package_name": "com.whatsapp"}'
```

---

## Full Agent Session — Example Flow

### Hermes / autonomous harness (standard flow)

```python
# 1. Start session
vrski_start_session("user_session_1")

# 2. Confirm the device is ready (the human already signed into Google once)
status = vrski_check_setup("user_session_1")
if not status["ready"]:
    if not status["signed_in"]:
        # The agent does NOT log in — Google 2FA needs the owner's phone.
        # Stop and tell the owner:
        #   "The Google account is signed out. Please run
        #    `bash scripts/login.sh` to sign back in, then ask me again."
        raise SystemExit("Device signed out — needs human sign-in")

# 3. Install any app by package name
vrski_install_app("user_session_1", "com.ubercab")    # Uber
vrski_install_app("user_session_1", "com.zomato.app")  # Zomato

# 4. Launch and interact
vrski_launch_app("user_session_1", "com.ubercab")

screen = vrski_get_screen("user_session_1")
# → elements: [{ type: "Button", text: "Sign in", clickable: true }, ...]

vrski_dismiss_popups("user_session_1")           # clear any welcome dialogs
vrski_tap("user_session_1", text="Sign in")
vrski_wait_for_element("user_session_1", text="Enter your mobile number", timeout=10)

# 5. Continue navigating — agent drives the entire flow autonomously
# ...

# N. Clean up
vrski_end_session("user_session_1")
```

The human signs into Google **once** with `scripts/login.sh`. After that, every
session `vrski_check_setup()` returns `ready: true` and the agent proceeds with
no human input — until the rare case where the account gets signed out, where it
hands back to the owner.

---

## Agent Best Practices

**Always read before acting.** Call `vrski_get_screen` before every action. App state changes between steps.

**Prefer text over coordinates.** `vrski_tap(text="Next")` never breaks across app versions. Coordinates do.

**Handle element-not-found gracefully.** A failed tap returns `{ "success": false, "screenshot_base64": "..." }`. Decode the screenshot, reason about what's on screen, then retry or navigate differently.

**Dismiss popups proactively.** Call `vrski_dismiss_popups` if an expected element doesn't appear after 2–3 retries. Play Store, Gmail, and system apps frequently show dialogs.

**CAPTCHA is a human signal.** If `vrski_signin_playstore` returns `{ "error": "captcha_detected" }`, surface it to the human. Once they complete it, call `vrski_get_playstore_account` to confirm the session is live and continue.

**Wait, don't assume.** After tapping something that triggers a screen transition, call `vrski_wait_for_element` with a known element on the next screen rather than sleeping a fixed duration.

---

## Handling Failures

Every failed action includes a `screenshot_base64` field. The agent can include this in its reasoning:

```python
result = vrski_tap(session_id, text="Continue")
if not result["success"]:
    # screenshot_base64 shows what's actually on screen
    # Decode and attach to next reasoning step
    screen = vrski_get_screen(session_id, include_screenshot=True)
    # Decide: dismiss popup? navigate back? wait?
```

The API **never** returns a 500 crash for bad UI state — only `{ "success": false }` with context. The server stays up.

---

## Phase 5 Hardening (built-in)

Vrski includes production reliability features out of the box:

- **Keep-alive**: Background task pings every active session's emulator every 30s. Auto-reconnects if ADB drops.
- **Retry logic**: `vrski/utils/retry.py` — `with_retry(fn, attempts=3, delay=1.0)` with exponential backoff. Use in custom harness plugins.
- **Screenshot on failure**: Every failed tap/action includes `screenshot_base64`. Agent can reason visually without a vision model call if needed.
- **Popup dismisser**: `/session/{id}/dismiss_popups` endpoint + `vrski_dismiss_popups` MCP tool.
- **Structured logging**: Every MCP tool call is logged as JSON: `{ tool, session_id, params, result, duration_ms }`.

---

## Recovery

**Emulator in bad state:**
```bash
bash scripts/reset_session.sh
# Kills emulator, wipes user data, restarts clean, re-inits uiautomator2
```

**Save a recovery snapshot after Play Store login:**
```bash
adb emu avd snapshot save vrski_loggedin
# Later, to restore:
adb emu avd snapshot load vrski_loggedin
```

**Check dependencies:**
```bash
bash scripts/check_deps.sh
```

---

## Project Structure

```
vrski/
├── vrski/
│   ├── adb/client.py           # ADB subprocess wrapper
│   ├── ui/
│   │   ├── element.py          # UIElement + Bounds dataclasses
│   │   ├── driver.py           # uiautomator2 device connection
│   │   ├── tree.py             # XML → UIElement parser
│   │   ├── finder.py           # find_by_text / find_by_id
│   │   └── actions.py          # tap / type / swipe / scroll
│   ├── credentials.py          # .env credential store (save / load Google creds)
│   ├── playstore/
│   │   ├── auth.py             # Gmail → Play Store sign-in automation
│   │   └── installer.py        # Play Store search + install flow
│   ├── session/                # SQLite session lifecycle
│   ├── api/                    # FastAPI server + routes
│   ├── mcp/
│   │   ├── server.py           # FastMCP — 23 tools
│   │   └── http_client.py      # MCP → FastAPI bridge
│   ├── emulator/
│   │   ├── config.py           # AVD constants
│   │   └── manager.py          # create/start/stop/snapshot AVD
│   └── utils/
│       ├── retry.py            # with_retry (async + sync)
│       └── logging.py          # structlog config
├── scripts/
│   ├── setup_avd.sh            # Create vrski_dev AVD (run once)
│   ├── login.sh                # Human one-time Google sign-in (run once)
│   ├── start_vrski.sh          # Start emulator + API server
│   ├── reset_session.sh        # Wipe app state + restart (keeps Google login)
│   └── check_deps.sh           # Verify adb / emulator / python
├── VRSKIAGENT.md               # Agent-facing guide (owner tags this)
├── tests/                      # 26 tests, mock + live
├── vrski_mcp_config.json       # Drop-in Claude Code MCP config
└── requirements.txt
```

---

## Running Tests

```bash
# Full suite (mock mode — no emulator needed)
pytest tests/ -v

# Live integration (emulator must be running)
VRSKI_MOCK=0 python tests/test_ui.py
```

Tests use `VRSKI_MOCK=1` / `VRSKI_SIMULATE=true` by default so CI passes without a connected device.

---

## License

MIT
