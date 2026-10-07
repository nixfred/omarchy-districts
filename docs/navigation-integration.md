# Camera journeys and observation replay

These components are isolated from window/session actions. `NavigationV2.qml` needs the existing theme object (`city`), `districts` from the current live city, `currentCamera` with `{x,y,zoom,yaw,tilt}`, the selected `targetDistrict`, and `motion`. Place it over the city body with `anchors.fill: parent`. `open("views"|"tour"|"replay")` opens the paginated panel; there are no scroll controls. The panel fits a 912×512 logical viewport in offscreen Qt Quick tests.

## Integration contract

- Handle `cameraRequested(camera,targetDistrict)` by stopping any other camera motion, applying/clamping the camera against the current renderer bounds and viewport, and optionally framing the still-existing target district. A missing target is not recreated; use the current city bounds. Root remains responsible for this bounds clamp because projection depends on the new camera orientation.
- Handle `tourDistrictRequested(id,instant)` by camera-only district framing. Set animation duration to zero for `instant`. This must never call a compositor focus/move action.
- Call `userTakeover()` **before** every manual pan/orbit/zoom/minimap/selection/search/viewpoint input. Handle `tourStopped(reason)` by stopping any still-running tour camera transition in the root. This is emitted by Stop, takeover and completion. `userTakeover()` stops further tour steps and replay playback; it does not move a real window.
- Tour sequencing captures the actual district IDs at explicit Start. It skips IDs no longer in the live district list. Newly observed districts join a subsequent tour. Each visit lasts 4.5 seconds. The final visit remains visible until completion. No automatic tour starts or repeats.
- Call `observe(enrichedLiveSnapshot,agentRecords,Date.now())` on **live** observations, before intercepting them for a replay view. Never call it with a replay snapshot. `agentRecords` accepts `{id|sessionId,parentId,workspace,status,statusSource|source|provider,provider}`. Native adapter status objects are retained as `{type,activeFlags}` (only `waitingOnApproval` and `waitingOnUserInput` flags). A legacy status string becomes `{type:string,activeFlags:[]}`. Status must be reported by the adapter, not inferred from CPU or message content. Agent records without a real workspace keep workspace 0; this never assigns them to a compositor workspace.
- Call `pauseTracking()` on closing/idle/disconnection. A later observation is a new baseline labeled “tracking resumed”; no events are invented across the gap. Use `suspend()` on app close/minimize to stop tour/playback, pause tracking and close the panel. Reset the buffer on plugin unload.
- Handle `replayRequested(snapshot,timestampMs)` with a **view-only** scene built from the supplied sanitized metadata. The component emits a deep copy; its history cannot be mutated by scene builders. Labels identify generic numbered districts/monitors and validated public app classes. Agent metadata contains only opaque IDs, parent IDs and adapter-reported status/source. Historic CPU is always unavailable. Show the persistent historical-view banner and timestamp.
- Keep a separate latest **live** snapshot while replaying. `liveRequested()` must restore that current snapshot and discard historical selection. Do not feed historical windows back into action transports. Guard every enter/focus/move/organization/agent-message/approval action during replay. Return live and require a fresh actual selection before action.
- Frame pruning preserves the selected timestamp as long as it remains retained. An expired selected frame returns to live automatically. Clearing history also returns live. Replay playback ends at the latest retained frame without claiming it is current.

## Private camera bookmarks

`persistenceRequested(request)` emits `list`, `save` or `delete`. Dispatch through a dedicated bounded `Process` to the co-located `history.py` helper:

```text
python3 history.py list
python3 history.py save --name NAME --camera JSON --target-district ID
python3 history.py delete --name NAME
```

Use argv directly, never shell interpolation. For a missing target omit `--target-district`. Set `persistenceBusy` for that one process and deliver its JSON to `acceptPersistence(result)`. Successful results contain `ok:true,schema:1,viewpoints:[...]`; failed results contain an explicit error. Run `list` initially or when the panel requests it. Test mode should use a private temporary `XDG_STATE_HOME` or a mock persistence response.

Only `camera.json` under `$XDG_STATE_HOME/districts` (default `~/.local/state/districts`) is written. It has mode 0600; atomic replacement uses a mode-0600 temporary file, fsync and a dedicated advisory lock. `architecture.json` is untouched. Names are at most 40 characters, capacity is 12, and an exact case-insensitive name replaces an existing bookmark. Delete is explicit. The helper limits input/read/output sizes and normalizes finite camera values. There is no replay persistence or agent/chat log read.

## Observation limits

Replay stores sampled metadata differences **since this component began tracking**, limited to 30 minutes, 120 frames and an estimated 512 KiB of UTF-16 JSON payload. No past logs, chats, titles, URLs, command lines, process IDs or private paths are captured. The minimal snapshot holds at most 512 districts/windows/agents; a truncated sample is marked. Sampling has a two-second minimum interval; transient events between samples can be missed. Frames are created only when retained metadata changes. Window appearance/disappearance means “observed” / “no longer observed,” not proof of an exact launch or close time. Baselines/resumed tracking have zero synthetic events. CPU differences do not create frames and historical lamps have unavailable CPU.

The size bound applies to retained serialized frame payload, not total Qt/JavaScript VM allocation. Rendering remains subject to the root's usual topology/resource caps.

## Validation

```sh
node tests/navigation.js
python -m unittest discover -s tests -p test_history.py -v
QT_QPA_PLATFORMTHEME=generic QT_QUICK_CONTROLS_STYLE=Basic QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qmltestrunner -input tests/tst_navigation.qml -o -,txt
```

Pure-controller tests cover normalization, actual tour membership, missing districts, metadata privacy, cadence, gap baselines, actual membership/reported-status changes and age/count/size caps. Python tests cover 0600 atomic state, unrelated architecture preservation, replacement/deletion/capacity, corruption limits and six concurrent writers. Offscreen Qt Quick tests cover tour takeover/completion/reduced-motion signals, replay/live/expiry/playback, persistence requests and all three panels at 912×512. These are fixture tests; native integrated Wayland focus and visual QA must be performed by the integration owner.
