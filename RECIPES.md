# Recipes — Vrski's Playbook Format

A **recipe** is a small, declarative spec for completing one task in one app. Recipes are
how Vrski scales to the long tail of Android: a new app or task is a **recipe, not new core
code**. They run through the normal Vrski API and the Phase 3 **trust gate**, so a sensitive
step (pay/send/delete) is gated behind owner approval automatically.

Recipes live in [`vrski/recipes.py`](./vrski/recipes.py) and run via
[`eval/run_recipe.py`](./eval/run_recipe.py).

## Anatomy

```python
Recipe(
    name="clock_start_timer",                 # unique id
    app="Clock",                              # display name
    package="com.google.android.deskclock",   # Android package
    launch_activity="com.android.deskclock.DeskClock",  # explicit activity (reliable launch)
    description="Start a countdown timer for {minutes} minutes.",
    params=["minutes"],                       # names of {placeholders}
    flow=[ ...steps... ],                     # ordered steps; string values may use {param}
    success_any=["Pause", "Reset"],           # task is done if ANY of these is on screen
)
```

### Step kinds

String values may contain `{param}` placeholders, filled from the invocation params.

| Step | Meaning |
|------|---------|
| `{"do": "dismiss"}` | clear blocking dialogs / coachmarks / permission prompts |
| `{"do": "wait_stable"}` | wait until the UI stops changing |
| `{"do": "tap", "text"\|"content_desc"\|"element_id": "..."}` | tap an element |
| `{"do": "type", "text": "..."}` | type into the focused field |
| `{"do": "scroll_to", "text": "..."}` | scroll toward an element |
| `{"do": "back"}` | hardware back |
| `{"do": "assert_text", "any": [...]}` | intermediate check |

## Run one

```bash
python3 eval/run_recipe.py clock_start_timer --param minutes=5
python3 eval/run_recipe.py contacts_add     --param name="Alex Rivera"
python3 eval/run_recipe.py wikipedia_lookup --param topic="Ada Lovelace"
```

## Current recipes (5 verticals)

| Recipe | App | Vertical |
|--------|-----|----------|
| `wikipedia_lookup` | Wikipedia | Information |
| `settings_battery` | Settings | Control |
| `calendar_today` | Calendar | Productivity |
| `contacts_add` | Contacts | People |
| `clock_start_timer` | Clock | Utility |

## Contribute a recipe

1. **Add a `Recipe(...)` to `vrski/recipes.py`** via `register(...)`. Prefer an explicit
   `launch_activity` (more reliable than the launcher intent). Keep `success_any` generic —
   assert on stable, task-defining controls (use `{param}` where the param is the proof).
2. **Tune it live** with `eval/run_recipe.py` against a real device until it passes.
3. **Ship a golden flow.** If the recipe is *idempotent* (repeatable), add it to the eval
   harness in [`eval/golden_flows.py`](./eval/golden_flows.py) via
   `as_eval_flow(RECIPES["your_recipe"], {params})`. Every recipe in the harness is guarded
   against app-UI drift. Non-idempotent recipes (e.g. one that leaves a running timer) stay
   out of the regression set but remain runnable.
4. **Stay honest.** Recipes target apps that don't fight automation. We do **not** write
   recipes that evade anti-bot / CAPTCHA / integrity checks — see [`HARD_MODE.md`](./HARD_MODE.md).

That's the flywheel: each contributed recipe is one more thing every agent can now do, with
a test that keeps it working.
