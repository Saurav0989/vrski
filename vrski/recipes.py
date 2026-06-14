"""Phase 4 — the Recipe / Playbook format.

A Recipe is a declarative, parameterized spec for completing ONE task in ONE app.
Recipes are the unit that lets Vrski scale to the long tail: a new app or task is a
recipe, not new core code. They run through the same Vrski API and the same Phase 3
trust gate as everything else, and each carries a `success_any` assertion so the eval
harness can guard it against app-UI drift.

Step kinds (string values may contain {param} placeholders filled from `params`):
  {"do": "dismiss"}                              clear blocking dialogs/coachmarks
  {"do": "wait_stable"}                          let the UI settle
  {"do": "tap", "text"|"content_desc"|"element_id": "..."}
  {"do": "type", "text": "..."}
  {"do": "back"}
  {"do": "assert_text", "any": [...]}            intermediate check
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Recipe:
    name: str
    app: str
    package: str
    description: str                       # human summary; may use {param}
    flow: List[Dict[str, Any]]            # ordered steps; string values may use {param}
    success_any: List[str]                # task is done if ANY of these strings is on screen
    params: List[str] = field(default_factory=list)
    launch_activity: Optional[str] = None  # explicit activity for reliable launching


def fill(value: Any, params: Dict[str, Any]) -> Any:
    """Substitute {param} placeholders in a string value (non-strings pass through)."""
    if isinstance(value, str) and params:
        for k, v in params.items():
            value = value.replace("{" + k + "}", str(v))
    return value


def render_flow(recipe: Recipe, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the recipe's steps with every {param} placeholder filled."""
    return [{k: fill(v, params) for k, v in step.items()} for step in recipe.flow]


def as_eval_flow(recipe: Recipe, params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a recipe + concrete params into an eval-harness golden flow."""
    steps = [{"do": "launch", "package": recipe.package, "activity": recipe.launch_activity}]
    steps += render_flow(recipe, params)
    steps += [{"do": "assert_text", "any": [fill(s, params) for s in recipe.success_any]}]
    return {"app": recipe.app, "name": recipe.name, "package": recipe.package, "steps": steps}


# --- the registry -----------------------------------------------------------

RECIPES: Dict[str, Recipe] = {}


def register(recipe: Recipe) -> Recipe:
    RECIPES[recipe.name] = recipe
    return recipe


def get(name: str) -> Recipe:
    return RECIPES[name]


# Owner's own everyday apps, signed in via the device Google account. No extra
# login, no anti-bot — exactly the long-tail tasks Vrski is for. (Tuned live.)

register(Recipe(
    name="clock_start_timer",
    app="Clock",
    package="com.google.android.deskclock",
    launch_activity="com.android.deskclock.DeskClock",
    description="Start a countdown timer for {minutes} minutes.",
    params=["minutes"],
    flow=[
        {"do": "dismiss"},
        {"do": "tap", "content_desc": "Timer"},
        {"do": "wait_stable"},
        {"do": "tap", "text": "{minutes}"},
        {"do": "tap", "text": "0"},
        {"do": "tap", "text": "0"},
        {"do": "tap", "content_desc": "Start"},
        {"do": "wait_stable"},
    ],
    success_any=["Pause", "Stop", "Add 1 min", "Reset"],
))

register(Recipe(
    name="contacts_add",
    app="Contacts",
    package="com.google.android.contacts",
    launch_activity="com.google.android.apps.contacts.activities.PeopleActivity",
    description="Add a contact named {name}.",
    params=["name"],
    flow=[
        {"do": "dismiss"},
        {"do": "tap", "content_desc": "Create contact"},
        {"do": "wait_stable"},
        {"do": "dismiss"},
        {"do": "tap", "text": "First name"},
        {"do": "type", "text": "{name}"},
        {"do": "tap", "text": "Save"},
        {"do": "wait_stable"},
    ],
    success_any=["{name}", "Contacts", "Edit contact"],
))

# --- Phase 5: more verticals, all via recipes (no core changes) --------------

register(Recipe(
    name="wikipedia_lookup",
    app="Wikipedia",
    package="org.wikipedia",
    launch_activity="org.wikipedia.main.MainActivity",
    description="Look up {topic} on Wikipedia.",  # Information vertical
    params=["topic"],
    flow=[
        {"do": "dismiss"},
        {"do": "tap", "content_desc": "Search"},
        {"do": "wait_stable"},
        {"do": "tap", "element_id": "org.wikipedia:id/search_card"},
        {"do": "wait_stable"},
        {"do": "type", "text": "{topic}"},
        {"do": "wait_stable"},
    ],
    success_any=["{topic}"],
))

register(Recipe(
    name="settings_battery",
    app="Settings",
    package="com.android.settings",
    launch_activity="com.android.settings.Settings",
    description="Open Battery settings.",  # Control vertical
    params=[],
    flow=[
        {"do": "dismiss"},
        {"do": "scroll_to", "text": "Battery"},
        {"do": "tap", "text": "Battery"},
        {"do": "wait_stable"},
    ],
    success_any=["Battery usage", "Battery Saver", "Battery percentage", "Adaptive", "Last charge"],
))

register(Recipe(
    name="calendar_today",
    app="Calendar",
    package="com.google.android.calendar",
    launch_activity="com.android.calendar.AllInOneActivity",
    description="Open my calendar agenda.",  # Productivity vertical
    params=[],
    # Assumes first-run onboarding is already completed (a one-time owner step,
    # like the Google sign-in). Asserts on stable agenda controls only.
    flow=[
        {"do": "dismiss"},
        {"do": "wait_stable"},
    ],
    success_any=["Jump to Today", "Create new event", "Show date picker", "Search"],
))
