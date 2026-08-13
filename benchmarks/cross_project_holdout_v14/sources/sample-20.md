---
id: hud-performance-meter
status: complete
branch: task/hud-performance-meter
---

# HUD Performance Meter Result

## Scope

- Initial task changed the allowed HUD/scene/style files: `BattleScene.ts`, `MultiplayerScene.ts`, `BattleHud.ts`, `src/styles.css`, and this result file.
- Follow-up feedback clarified the Multiplayer HUD needs multiplayer-specific diagnostics, so `src/multiplayer/client.ts` now exposes the existing `pong` message through an optional handler.
- Avoided simulation, input, multiplayer protocol/server, camera behavior, assets, docs, and gameplay tuning.

## Changes

- Added a compact reusable `HudPerformanceMeter` DOM widget that shows local FPS and frame time in milliseconds.
- Added the meter to the Single Player HUD, centered at the top of the existing HUD grid so it stays away from the touch controls and bow aim area.
- Embedded the Multiplayer meter inside the existing Multiplayer HUD instead of floating it separately.
- Added Multiplayer HUD diagnostics for RTT, snapshot age, and received snapshot rate so multiplayer lag can be separated from render frame time.
- Fed frame data from Phaser scene `deltaMs`, using a light smoothing pass and throttled text updates so the readout is readable without changing gameplay or networking behavior.
- Used the existing multiplayer ping/pong protocol for RTT; no server or protocol changes were needed.
- Styled the meter as a small non-interactive HUD panel, with responsive compact sizing for short landscape screens.

## Checks

- Passed: `npm run typecheck`
- Passed: `npm test`

Note: the first `npm run typecheck` attempt failed because `node_modules` was missing in this worktree. I ran `npm ci` from the existing lockfile, then reran the listed checks successfully.

## Follow-up tasks

- If multiplayer still feels sticky with healthy RTT and snapshot age, create a separate gameplay/networking task for interpolation or client prediction. This HUD task intentionally does not change those systems.

## Follow-up: Runtime Refactor

After multiplayer performance feedback, the task scope expanded into a WoC-style runtime boundary:

- Added `WorldRuntime`, `LocalWorldRuntime`, `OnlineWorldRuntime`, and `ServerWorldRuntime`.
- Routed Single Player through `LocalWorldRuntime` while preserving bow audit, frame hitch audit, HUD, audio, and gameplay behavior.
- Moved Multiplayer WebSocket sync, snapshot buffering, local prediction, interpolation, ping/rate metrics, and event collection out of `MultiplayerScene` into `OnlineWorldRuntime`.
- Routed the WebSocket server through `ServerWorldRuntime`, keeping socket lifecycle separate from simulation ticking and snapshot construction.
- Added runtime tests for offline and authoritative multiplayer shooting paths.

Additional checks:

- Passed: `npm run typecheck`
- Passed: `npm test`
- Passed: `npm run build` with the existing Vite large chunk warning.
- Passed: local Playwright multiplayer smoke against temporary Vite + WebSocket servers; HUD showed `Connected`, `player-1`, network metrics, and no page errors.

Follow-up recommendation:

- The next latency-feel improvement should be implemented inside `OnlineWorldRuntime`, not in Phaser scenes: either stronger local action prediction for shooting visuals, or a fuller shared `SimulationEvent` stream so offline and online audio/FX consume the same event surface.
