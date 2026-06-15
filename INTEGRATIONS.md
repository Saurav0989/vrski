# Integrating Vrski with an Agent Harness

Vrski exposes the phone as **MCP tool calls**, so any MCP-capable agent harness can drive it.
The one-time human setup (create the AVD, sign into Google once) is in
[`GUIDE.md`](./GUIDE.md); this doc is about wiring your harness to the running runtime.

## Start the runtime

```bash
bash scripts/start_vrski.sh     # boots the emulator + the control API on :7070
```

## Claude Code

```bash
claude mcp add vrski python -m vrski.mcp.server
```

or add to your `.mcp.json` (a drop-in is in [`vrski_mcp_config.json`](./vrski_mcp_config.json)):

```json
{
  "mcpServers": {
    "vrski": { "command": "python", "args": ["-m", "vrski.mcp.server"],
               "env": { "VRSKI_API_URL": "http://localhost:7070" } }
  }
}
```

## Hermes (Nous Research)

Hermes is MCP-capable. Add the same server to its MCP config:

```json
{ "mcpServers": { "vrski": { "command": "python", "args": ["-m", "vrski.mcp.server"] } } }
```

Then point Hermes at [`VRSKIAGENT.md`](./VRSKIAGENT.md) — it encodes the reliable drive loop
(read → `wait_stable` → act → confirm with `screen_changed`), the "Continue with Google"
login flow, and when to hand back to the owner. That file is the agent's operating manual.

## Any MCP harness

The server is plain MCP over stdio (`python -m vrski.mcp.server`, reading `VRSKI_API_URL`).
Register it however your harness registers MCP servers.

## No MCP? Use the REST API

The control API at `http://localhost:7070` is the underlying surface — wrap it in a thin
plugin. See the REST reference in [`README.md`](./README.md).

## The tool surface (what your agent gets)

- **Perceive:** `vrski_get_screen` (salient tree), `vrski_look` (tree + screenshot),
  `vrski_wait_stable`, `vrski_wait_for_element`, `vrski_check_wall`.
- **Act:** `vrski_tap` (disambiguated, returns `screen_changed`), `vrski_type` (fails loudly
  with no focused field), `vrski_swipe`, `vrski_scroll_to`, `vrski_back/home/recent_apps`.
- **Apps:** `vrski_install_app`, `vrski_launch_app`, `vrski_close_app`, `vrski_is_installed`,
  `vrski_list_installed`, `vrski_dismiss_popups`.
- **Trust:** `vrski_set_policy`, `vrski_approve`, `vrski_get_audit`, `vrski_pause`,
  `vrski_resume`.
- **Sessions:** `vrski_start_session` (per-device via `emulator_serial`), `vrski_end_session`,
  `vrski_get_session_status`, `vrski_list_sessions`, `vrski_check_setup`.

Full signatures: [`README.md`](./README.md). Reliable usage patterns: [`VRSKIAGENT.md`](./VRSKIAGENT.md).
