"""Unit tests for the recipe format."""
from vrski.recipes import RECIPES, Recipe, render_flow, as_eval_flow, fill


def test_fill_substitutes_params():
    assert fill("set {minutes} min", {"minutes": 5}) == "set 5 min"
    assert fill("no placeholder", {"x": 1}) == "no placeholder"
    assert fill(123, {"x": 1}) == 123  # non-strings pass through


def test_render_flow_fills_every_step():
    r = Recipe(
        name="t", app="T", package="p", description="d",
        params=["name"],
        flow=[{"do": "type", "text": "{name}"}, {"do": "tap", "content_desc": "Save"}],
        success_any=["{name}"],
    )
    steps = render_flow(r, {"name": "Alex"})
    assert steps[0]["text"] == "Alex"
    assert steps[1]["content_desc"] == "Save"  # untouched


def test_as_eval_flow_wraps_launch_and_assert():
    r = RECIPES["clock_start_timer"]
    flow = as_eval_flow(r, {"minutes": "5"})
    assert flow["steps"][0]["do"] == "launch"
    assert flow["steps"][0]["package"] == r.package
    assert flow["steps"][-1]["do"] == "assert_text"
    # the {minutes} placeholder is filled
    assert any(s.get("text") == "5" for s in flow["steps"])


def test_registry_recipes_are_well_formed():
    assert "clock_start_timer" in RECIPES and "contacts_add" in RECIPES
    for r in RECIPES.values():
        assert r.package and r.flow and r.success_any
        for step in r.flow:
            assert "do" in step
