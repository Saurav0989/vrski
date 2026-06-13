# Vrski Eval Harness

The regression net for reliability. "Better and better" only means something if we
can watch a number move — this is that number.

It runs a set of **golden flows** (real multi-step tasks on login-free apps) against a
live Vrski API and reports the success rate. No Google account needed.

## Run it

With the emulator + API up (see the repo `GUIDE.md` / `scripts/start_vrski.sh`):

```bash
python3 eval/run_eval.py --repeats 3
```

It prints per-run PASS/FAIL, per-app totals, and an overall rate, then checks the
**Phase 1 exit criterion: ≥ 4 apps covered and ≥ 90% overall**. Exit code is 0 when met.

## Current flows (`golden_flows.py`)

| App | Flow | Proves |
|-----|------|--------|
| Settings | home → Network & internet | launch, read, exact-text tap, navigate |
| Clock | tabs visible | launch, dismiss, read |
| Wikipedia | search → suggestions | search tab, focus input, type-into-focused, read results |
| Dialer | tabs visible | first-run dismissal, read |
| Contacts | home visible | first-run dismissal, read |

Latest local run: **15/15 = 100%**, 5 apps.

## Adding a flow

Append a dict to `FLOWS` in `golden_flows.py`. Steps: `launch`, `wait_stable`,
`dismiss`, `tap`, `type`, `back`, `assert_text`, `assert_activity`. Keep asserts
generous (`any` of several strings) so they survive minor app-version wording changes.

This declarative flow format is the seed of the per-app **recipe** format that the
roadmap's Phase 4 generalizes — every recipe should ship a golden flow that runs here.
