# VRSKIAGENT — How an AI Agent Uses Vrski

> **You are an AI agent (Hermes, Claude Code, OpenClaw, …). This file tells you how to control a real Android phone for your owner through Vrski — reliably.**

Your owner finished the one-time setup: they cloned Vrski and signed a Google account into the emulator **by hand**. **That part is done. Do not redo it, and never ask for their Google password.** Your job starts now.

---

## What Vrski gives you

Vrski exposes a real Android device as **MCP tool calls**. It is **semantic-first, vision-backed**:

- **Semantic-first:** you read the screen as a structured JSON list of elements (the accessibility tree) and act by `text` / `content_desc` / `element_id`. No vision model needed for most screens.
- **Vision-backed:** some screens (WebView pages, parts of Compose UIs, games) barely show up in the tree. Vrski tells you (`has_webview` / `low_signal`) and gives you a screenshot via `vrski_look` so you can reason visually and tap by coordinates. **Semantic when you can, visual when you must.**

```
vrski_get_screen()  → JSON elements (filtered to what matters) + flags
vrski_look()        → elements + a screenshot, for screens the tree can't describe
vrski_tap(text="Log in")  → finds the right element and taps it
vrski_type(text="…")      → types into the focused field (fails loudly if none)
```

The emulator already has the owner's Google account signed in, so the Play Store works and you can install apps and complete **"Continue with Google"** logins yourself.

---

## Step 1 — Wire yourself up (once per machine)

```bash
cd ~/.hermes/vrski            # the repo your owner cloned
bash scripts/start_vrski.sh   # boots the emulator + Vrski control API
```

Register the MCP server with your harness:

```bash
# Claude Code:
claude mcp add vrski python -m vrski.mcp.server
# Hermes / any MCP harness — add to your MCP config:
#   { "mcpServers": { "vrski": { "command": "python", "args": ["-m", "vrski.mcp.server"] } } }
```

Confirm you're connected and the device is ready:

```
vrski_start_session("owner")
vrski_check_setup("owner")
  → expect { "ready": true, "signed_in": true, "active_account": "…@gmail.com" }
```

`ready: true` means the device is signed in and usable. **Note:** `has_credentials` will be `false` and that is correct — nothing is stored, by design. The account lives on the device. If `ready` is true, proceed.

> `vrski_start_session` is safe to call again — if the API restarted, it re-attaches to the existing session instead of erroring.

---

## Step 2 — The reliable core loop

Every task is the same rhythm. **Never act blind, and never assume an action worked — confirm it.**

```
1. vrski_get_screen("owner")        # read what's actually on screen
2. (if low_signal / has_webview)    # the tree can't describe this screen →
       vrski_look("owner")          #   get a screenshot, reason visually
3. decide which element to act on    # by text / content_desc / element_id
4. vrski_tap / vrski_type / vrski_swipe
5. vrski_wait_stable("owner")       # let the screen settle after a transition
6. go back to 1                      # confirm the result, then continue
```

What makes it smooth — use these, they're why driving Vrski is reliable:

- **`vrski_wait_stable("owner")` after anything that changes screens** (launching an app, tapping a button that navigates). It blocks until the UI stops changing — far more reliable than a fixed delay.
- **Trust `screen_changed`.** `vrski_tap` and `vrski_type` return `screen_changed: true/false`. If you expected a transition and it's `false`, you tapped a no-op — **don't repeat the same tap in a loop.** Re-read, `vrski_dismiss_popups`, or `vrski_look` and try a different target.
- **Tap is disambiguated for you.** If several elements share a label, `vrski_tap` picks the actionable one (a button/list-row over a text field that merely contains the same words) and tells you `matched_count` / `ambiguous`. If `ambiguous` and it chose wrong, tap by `element_id` or coordinates instead.
- **Type needs a focused field.** `vrski_type` types into whatever is focused. If nothing is, it returns `success: false` with a screenshot — it will **not** silently type into nothing. So: tap the input field first, then `vrski_type`.
- **`vrski_get_screen` is filtered by default** (`salient=true`) — it drops empty containers, the status bar, and keyboard keys so you see the ~dozen elements that matter, not 100+. Pass `salient=false` if you genuinely need the raw tree.

---

## Step 3 — Logging into apps (read this — it's where agents get stuck)

When an app shows a sign-in screen, **call `vrski_check_wall("owner")` first.** It classifies the screen and tells you whether *you* can proceed or a human is required:

| `wall` | `human_required` | What you do |
|--------|------------------|-------------|
| `login` + `google_sso_available: true` | **false** | **You can do it.** Tap "Continue with Google" (below). |
| `login` (email/phone only) | true | No agent-completable SSO. Tell the owner. |
| `otp` | true | A one-time code went to the owner's phone/email. Ask them; don't guess. |
| `2fa` | true | Google "verify it's you" — only the owner's phone can approve. |
| `bot_block` | true | An anti-bot / CAPTCHA check (PerimeterX, etc.). **You cannot solve it.** Surface it. |
| `none` | false | No wall — carry on. |

**"Continue with Google" — you can complete this yourself, no password, no OTP:**
```
vrski_tap("owner", text="Continue with Google")
vrski_wait_stable("owner")
# Android shows an account picker: "Choose an account → to continue to <App>"
vrski_tap("owner", text="<owner's @gmail.com>")   # select the device account
vrski_wait_stable("owner")
# OAuth completes and returns to the app — you're logged in.
```

**Reality check on commercial apps (food / ride / banking):** many run **anti-bot detection** and will either refuse to install ("device not compatible") or, right after login, throw a "prove you're not a robot" block. This is **not** something you did wrong and **not** something better tapping fixes — it's the app detecting the environment. When `vrski_check_wall` returns `bot_block`, **stop and tell the owner** (include the screenshot); that app may need a real device. Apps that don't fight automation (messaging, utilities, many services) work great.

### Other common tasks

**"Install <app>"**
```
vrski_install_app("owner", "com.example.app")   # installs from the Play Store
vrski_is_installed("owner", "com.example.app")   # confirm
```

**"Reply to the latest message"** (messaging apps are reliable — no anti-bot)
```
vrski_launch_app("owner", "<messaging app>")
vrski_wait_stable("owner"); vrski_get_screen("owner")
vrski_tap("owner", text="<contact name>")
vrski_tap("owner", content_desc="Message")       # tap the input field first
vrski_type("owner", text="…")                    # then type
vrski_tap("owner", content_desc="Send")
```

---

## Golden rules

1. **Read before every action; confirm after.** `vrski_get_screen` first, then check `screen_changed` / re-read. The screen changes between steps — never assume.
2. **Wait for stable, don't sleep.** Use `vrski_wait_stable` after transitions.
3. **When the tree is thin, look.** If `low_signal` or `has_webview` is true (or an expected element just isn't there), call `vrski_look` and reason from the screenshot.
4. **Tap the field before you type.** `vrski_type` only works on a focused input.
5. **Don't loop on a no-op.** `screen_changed: false` when you expected change = try something different (`vrski_dismiss_popups`, a different element, or `vrski_look`).
6. **Check the wall before fighting a login.** `vrski_check_wall`. Do "Continue with Google" yourself; hand back `otp` / `2fa` / `bot_block` / CAPTCHA to the owner.
7. **Never sign into Google yourself, never ask for the owner's password.** If `vrski_check_setup` → `signed_in: false`, tell the owner: *"The Google account is signed out — please run `bash scripts/login.sh`."*
8. **One session per owner.** Reuse the same `session_id`; `vrski_end_session` only when fully done.

---

## Tool quick reference

| Tool | Purpose |
|------|---------|
| `vrski_start_session(session_id)` | Begin / re-attach a session (idempotent) |
| `vrski_check_setup(session_id)` | Is the device ready & signed in? (`ready` true = go) |
| `vrski_get_screen(session_id, salient=True)` | Read on-screen elements as JSON (+ `has_webview`/`low_signal` flags) |
| `vrski_look(session_id)` | Elements **+ screenshot** — for WebView/Compose/sparse screens |
| `vrski_wait_stable(session_id)` | Block until the screen stops changing |
| `vrski_wait_for_element(session_id, text=…)` | Block until a specific element appears |
| `vrski_check_wall(session_id)` | Classify a login/verification wall; who must act |
| `vrski_tap(session_id, text=… / element_id=… / content_desc=…)` | Tap (disambiguated; returns `screen_changed`) |
| `vrski_type(session_id, text=…)` | Type into the focused field (fails loudly if none) |
| `vrski_swipe(…)` / `vrski_scroll_to(session_id, text=…)` | Scroll |
| `vrski_back / vrski_home / vrski_recent_apps(session_id)` | Hardware keys |
| `vrski_install_app / vrski_launch_app / vrski_close_app / vrski_uninstall_app(session_id, package_name)` | App lifecycle |
| `vrski_is_installed / vrski_list_installed(session_id)` | Query apps |
| `vrski_dismiss_popups(session_id)` | Clear blocking dialogs / permission prompts / coachmarks |
| `vrski_get_playstore_account(session_id)` | Which Google account is active |

Full signatures and return shapes: see `README.md`.

---

## When something breaks

| Symptom | What to do |
|---------|-----------|
| `vrski_*` calls all fail / connection error | API/emulator isn't running. `bash scripts/start_vrski.sh`. |
| `vrski_check_setup` → `signed_in: false` | Account signed out. Ask the owner to run `bash scripts/login.sh`. |
| An element you expected isn't in the tree | `vrski_look` (it may be a WebView/Compose screen) and act on the screenshot; or `vrski_dismiss_popups` then re-read. |
| `screen_changed: false` but you expected a change | You hit a no-op. Try a different element / `vrski_look`; don't repeat the same tap. |
| App shows a CAPTCHA / "not a robot" / `bot_block` | Anti-bot detection. You can't solve it — surface it to the owner (with the screenshot). |
| App's own login wall (`otp` / email / phone) | `vrski_check_wall`; hand the human-only part back to the owner. |
| Emulator stuck / weird state | `bash scripts/reset_session.sh` (wipes app state, keeps the Google login). |

---

**In one line:** the owner signed in once; you drive the phone — read the screen (or `vrski_look` when it's opaque), act by element, `vrski_wait_stable`, confirm with `screen_changed`, do "Continue with Google" logins yourself, and hand back to the owner only at a human-only wall (`otp` / `2fa` / `bot_block` / CAPTCHA).
