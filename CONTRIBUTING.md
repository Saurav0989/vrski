# Contributing to Vrski

Vrski is the agent's hands for the **long tail** of Android — apps that have no API and don't
fight automation. The fastest way to help is to **add a recipe**; the most important rule is
**we don't evade anti-bot systems.**

## The one non-negotiable: detect, don't evade

Vrski **never** solves CAPTCHAs, spoofs device integrity / Play Integrity, fingerprint-spoofs
a human session, or otherwise defeats an app's anti-automation controls. When we hit such a
wall we **detect it** (`vrski_check_wall`) and **hand back to the owner**. PRs that try to beat
anti-bot will be declined. This is both an ethics call and what lets Vrski be a clean standard.
See [`HARD_MODE.md`](./HARD_MODE.md).

## Add a recipe (the best first contribution)

See [`RECIPES.md`](./RECIPES.md). In short:
1. Add a `Recipe(...)` to `vrski/recipes.py`.
2. Tune it live: `python3 eval/run_recipe.py <name> --param k=v`.
3. If idempotent, add a golden flow in `eval/golden_flows.py` so the harness guards it.

## Running the checks

```bash
# unit + integration tests (mock — no device needed)
python3 -m pytest tests/ --ignore=tests/test_mcp.py

# the reliability eval harness (needs the emulator + API running)
python3 eval/run_eval.py --repeats 3
```

`tests/test_mcp.py` is skipped because it needs the `mcp` SDK, which isn't required to run the
runtime. Every behavior change should keep the mock suite green and, ideally, add a test.

## Where things live

| Path | What |
|------|------|
| `vrski/ui/` | the semantic UI layer (tree parse, find, tap/type/swipe) |
| `vrski/control.py` | the trust gate: classify sensitive actions, policy, approvals, audit |
| `vrski/walls.py` | login/CAPTCHA/OTP wall detection + hand-back |
| `vrski/recipes.py` | the recipe format + registry |
| `vrski/api/` | the FastAPI control server |
| `vrski/mcp/` | the MCP server (the agent-facing tool surface) |
| `eval/` | the reliability harness + recipe runner |
| `tests/` | unit + integration tests |

## Principles to keep

- **Semantic-first, vision-backed** — accessibility tree by default, screenshot fallback when it can't describe the screen.
- **Honest signals** — a tool fails loudly when it didn't do the thing.
- **The human is the root of trust** — sensitive/irreversible actions need owner approval.
- **Measure reliability** — if you change the drive loop, watch the eval number.
