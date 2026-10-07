# Development

This repository is the complete Districts project. It uses Omarchy’s shell imports at runtime and does not depend on an original task directory, Mycelium or Infomarchy. Quickshell loads QML/JavaScript; Python helpers use the standard library.

## Layout

| Path | Purpose |
| --- | --- |
| `manifest.json` | Plugin identity, version and versioned entry point |
| Versioned runtime directory | Installed QML, JavaScript and Python helpers |
| Root runtime source copies | Native/portable fixture inputs; byte parity is required |
| `install.py` | Validated staging, backup receipt and optional scoped activation |
| `tests/` | Executable behavior checks and controlled native fixtures |
| `docs/images/` | Illustrative hero and sanitized documentation images |
| `tools/check-project.py` | Release completeness, runtime parity and local links |
| `verification/RELEASE.json` | Sanitized evidence for a particular release |

Use the entry point in the manifest to determine the current runtime path. Update the validated installer file list and parity checks when adding runtime helpers. Keep source edits separate from the installed plugin.

## Portable checks

Python 3.10+ and Node.js 18+ are sufficient for portable checks; no Python package installation is needed. Run from the repository root:

```bash
python3 tools/check-project.py
python3 -m unittest discover -s tests -p 'test_*.py'
for check in tests/*.js; do node "$check"; done
```

Tests should exercise executable behavior, failures and side effects. Source-string matching alone does not establish that a feature works. Use fixture dependencies for process counters, compositor responses and session transports. Never send a real user instruction merely to prove that a button is wired.

CI should run all relevant portable cases for the exact release commit. It does not replace native renderer, monitor-scale, focus or interaction verification.

## Native fixtures

Native tests need an awake Omarchy Wayland session, Quickshell with QtTest support, and `OMARCHY_PATH` pointing to the installation or checkout supplying `shell/Commons`, `shell/Ui` and `shell/services`.

Representative commands:

```bash
python3 tests/grouping.py
python3 tests/pagination.py
python3 tests/interaction.py
python3 tests/application.py
python3 tests/activity_native.py
python3 tests/resolutions.py
python3 tests/performance.py
```

Use synthetic metadata, temporary state and fixture-owned processes. Simulated actions remain in the fixture; real window moves and agent instructions must not be test substitutes. Fixture surfaces can be visible Wayland windows. Disabling keyboard focus and pointer input helps, but native maximize/map behavior still requires explicit compositor verification. Use an isolated hidden fixture workspace where necessary and record any temporary rule and its cleanup.

Record logical viewport size separately from physical pixel dimensions and compositor scale. Include small/wide viewports, enlarged labels, light/dark themes, reduced motion, empty/disconnected/error states, modal pages and action results. Full 360° projection requires orientation-specific depth, visible-face, picking and label checks. Closed/minimized views must stop collection, tour/replay playback and animation.

A fixture test, a live backend check and live visible interaction are distinct. Report which ran and what remains. Resource samples are short measurements of their specified workload, not machine-wide guarantees.

## Sessions and privacy

The [session guide](SESSIONS.md) defines supported transport boundaries. Provider status must come from explicit records or API responses; CPU, process trees and inferred terminal contents cannot establish task progress or agent parentage. Metadata inventory must not preload reply text. Reply reads target one explicitly selected session.

Session tests use mocked protocol peers and bounded public examples. An existing native client owns approvals. No test may lower permissions, resume a user session, create a competing process or inject terminal input. A queue response establishes queue acceptance only. Preserve a submission identity through uncertain outcomes and do not automatically resend.

Replay tests must cover age/count/payload caps, observation gaps, missing objects, return-to-live behavior and action locks. Replay observations must omit private labels, paths, PIDs, replies and drafts, and must never enter action transports.

## Documentation captures and review

Capture public screenshots from the plugin’s native surface with controlled fixture data and public app names. Do not capture a live user desktop, private replies, credentials, local source paths or terminal text. Existing images can illustrate an earlier release only when clearly labeled; replace them with final-version fixtures before advertising new controls in screenshots.

`tests/docs_capture.py` is a documentation tool, not an ordinary verification run. Crowded stress fixtures and repeated long labels belong in private verification output, not showcase images.

Raw logs, captures, backups and independent-review prompts/responses stay outside public source or in ignored local directories. Publish only a truthful sanitized release/review summary bound to a full source commit and runtime digest. Historical review credits do not constitute a new release audit. Inspect tracked files before publication and verify remote CI for the exact pushed SHA.

Historical installation diagnostics such as `tests/activation_health.py` may depend on private receipts from their original environment; they are not portable checkout tests. `tests/live_bridge.py` reads actual desktop metadata and belongs only in an explicitly requested live diagnostic.

## Stage, activate and recover

Follow the [installation guide](../README.md#install-on-an-existing-omarchy-desktop). To validate staging without enabling:

```bash
python3 install.py --destination /tmp/districts-preview/nixfred.districts \
  --receipt /tmp/districts-preview/installation.json
```

Staging still requires Omarchy’s plugin validator. Live activation uses supported plugin discovery/enable APIs. A scoped rescan can recreate plugin components/services; it must not restart the entire shell. Account for shell API differences, retain current bar placement, and compare current live/disk config before and after activation.

Keep the receipt and backup locally. Rollback closes Districts, restores its previous runtime and rescans. Restore saved configuration only after comparing it with the latest state so recovery cannot erase unrelated work.
