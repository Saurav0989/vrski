"""Golden flows for the Vrski eval harness.

Each flow is a declarative list of steps run against a live device through the
Vrski API. They use only login-free apps so the suite runs with no Google account.
This is also the seed of the "recipe" format that Phase 4 generalizes.

Step kinds:
  {"do": "launch", "package": "..."}         force-stop then launch (clean state)
  {"do": "wait_stable", "timeout": 10}        wait until the UI settles
  {"do": "dismiss", "times": 2}               clear blocking dialogs/coachmarks
  {"do": "tap", "text"|"content_desc"|"element_id"|"x"/"y": ...}
  {"do": "type", "text": "..."}
  {"do": "back"}
  {"do": "assert_text", "any": [...]}         pass if ANY string is on screen
  {"do": "assert_activity", "contains": "..."}
"""

FLOWS = [
    {
        "app": "Settings",
        "name": "settings_home_and_network",
        "package": "com.android.settings",
        "steps": [
            {"do": "launch", "package": "com.android.settings"},
            {"do": "wait_stable"},
            {"do": "assert_text", "any": ["Network & internet", "Connected devices", "Battery", "Search settings", "Apps"]},
            {"do": "tap", "text": "Network & internet"},
            {"do": "wait_stable"},
            {"do": "assert_text", "any": ["Internet", "Wi-Fi", "Wifi", "Airplane mode", "SIMs", "Hotspot"]},
        ],
    },
    {
        "app": "Clock",
        "name": "clock_tabs",
        "package": "com.google.android.deskclock",
        "steps": [
            {"do": "launch", "package": "com.google.android.deskclock"},
            {"do": "wait_stable"},
            {"do": "dismiss"},
            {"do": "assert_text", "any": ["Alarm", "Clock", "Timer", "Stopwatch", "Bedtime"]},
        ],
    },
    {
        "app": "Wikipedia",
        "name": "wiki_search_suggestions",
        "package": "org.wikipedia",
        "steps": [
            {"do": "launch", "package": "org.wikipedia"},
            {"do": "wait_stable"},
            {"do": "dismiss"},
            {"do": "tap", "content_desc": "Search"},
            {"do": "wait_stable"},
            {"do": "tap", "element_id": "org.wikipedia:id/search_card"},
            {"do": "wait_stable"},
            {"do": "type", "text": "Alan Turing"},
            {"do": "wait_stable"},
            {"do": "assert_text", "any": ["Alan Turing Institute", "English computer scientist", "Alan Turing law"]},
        ],
    },
    {
        "app": "Dialer",
        "name": "dialer_tabs",
        "package": "com.google.android.dialer",
        "steps": [
            {"do": "launch", "package": "com.google.android.dialer"},
            {"do": "wait_stable"},
            {"do": "dismiss", "times": 3},
            {"do": "wait_stable"},
            {"do": "assert_text", "any": ["Favorites", "Recents", "Contacts", "Keypad", "Search contacts & places"]},
        ],
    },
    {
        "app": "Contacts",
        "name": "contacts_home",
        "package": "com.google.android.contacts",
        "steps": [
            {"do": "launch", "package": "com.google.android.contacts"},
            {"do": "wait_stable"},
            {"do": "dismiss", "times": 3},
            {"do": "wait_stable"},
            {"do": "assert_text", "any": ["Contacts", "Create contact", "Add a contact", "Search contacts", "Fix & manage"]},
        ],
    },
]

# --- Phase 4 recipes, surfaced as golden flows so the harness guards them too ---
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))
from vrski.recipes import RECIPES as _RECIPES, as_eval_flow as _as_eval_flow  # noqa: E402

# Only *idempotent* recipes belong in the regression harness. clock_start_timer is a
# proven recipe (run it with `eval/run_recipe.py`) but is NOT repeatable here: once it
# sets a timer the keypad disappears, and clearing a running timer is a destructive
# action that (correctly) needs owner approval. contacts_add just adds a fresh contact
# each run, so it guards cleanly.
FLOWS += [
    _as_eval_flow(_RECIPES["contacts_add"], {"name": "Sam Carter"}),
    _as_eval_flow(_RECIPES["wikipedia_lookup"], {"topic": "Ada Lovelace"}),
    _as_eval_flow(_RECIPES["settings_battery"], {}),
    _as_eval_flow(_RECIPES["calendar_today"], {}),
    _as_eval_flow(_RECIPES["settings_storage"], {}),
    _as_eval_flow(_RECIPES["contacts_search"], {"query": "Alex"}),
    _as_eval_flow(_RECIPES["keep_search"], {"query": "milk"}),
    _as_eval_flow(_RECIPES["maps_search"], {"place": "coffee"}),
    _as_eval_flow(_RECIPES["gmail_search"], {"query": "Google"}),
    _as_eval_flow(_RECIPES["youtube_search"], {"query": "lofi"}),
    _as_eval_flow(_RECIPES["chrome_open_url"], {"url": "wikipedia.org"}),
]
