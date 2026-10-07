# Provider legend and quota evidence

The legend is independent of Infomarchy and Burn Bar. Its shipped reader is
`provider_metrics.py`; it imports no installed widget code, calls no widget IPC,
reads no credentials or transcripts, starts no authenticated provider process,
and makes no network request. Missing optional shared metadata produces an
explicit unavailable result. The four provider identities remain visible.

## Source matrix

| Provider | Supported optional source | Actual units and observation proof | Pacing support and limits |
| --- | --- | --- | --- |
| Claude | `$XDG_CACHE_HOME/omarchy/agent-usage/claude-limits.json`; otherwise shared usage JSON | Probe `{fetchedAtMs, limits:[{label, percent, resetsAt}]}`. `percent` is a 0–1 fraction. `fetchedAtMs` is the successful quota probe stamp; the shared record's `updatedAt` can instead be a rewrite of cached limits. | Explicit `(5-hour)` or `(7-day)` duration plus reset supports an even-pace model. Plain `Fable Weekly` alone does not prove a start. No raw OAuth/credential retrieval. |
| Codex | `$XDG_STATE_HOME/omarchy/agents/usage/codex.json`; the session helper also reads an existing authenticated daemon's read-only `account/rateLimits/read` result | Generic shared `{limits:[{label, percent, resetsAt}]}` needs an explicit quota measurement stamp; `updatedAt` alone is insufficient. Daemon windows report `usedPercent` on 0–100 scale, `windowDurationMins` and `resetsAt` in Unix seconds. Integration converts to fraction, `durationMs`, epoch milliseconds, and records the local read timestamp. | API duration plus reset supports an even-pace model; `reset-duration` is a **modeled start**, not a provider-declared start. A current read is an observation of a provider snapshot, not proof of when the upstream quota first changed. `ordinaryUsageAllowed: null` is unknown; no permission/unblocking inference from usage percentage. |
| Grok | Optional canonical shared usage JSON | Same normalized fraction/reset rows; explicit quota observation stamp required. No such shared file was present in the local metadata survey. | Installed reference code reads a startup billing snapshot's `creditUsagePercent` on 0–100 scale and `currentPeriod.end`; that code/log is **not** a runtime source for this reader. Without supported stamped metadata, quota and pacing remain unavailable. |
| Kimi | Optional canonical shared usage JSON | Explicit `limitsMeasuredAt`, `measuredAt` or `fetchedAtMs` plus fraction/reset rows required. No canonical Kimi shared file was present in the local survey. | The inspected reference has a `{measuredAt, limits}` legacy cache from Kimi `/usages`; its 5-hour request window and monthly credit ratios are distinct. `--reference-kimi-cache` can explicitly import the existing plain snapshot, but is **off by default**. A plain monthly label has no time credit unless the source provides an actual start or an explicit duration. No API key retrieval. |

Canonical shared records live at
`$XDG_STATE_HOME/omarchy/agents/usage/{grok,claude,codex,kimi}.json`.
The optional legacy Kimi input is
`$XDG_STATE_HOME/omarchy/burnbar/kimi-usage.json`; it is not required for installation
or operation, and no Burn Bar service is invoked. The local default reader survey
returned fresh stamped Claude metadata; Codex shared quota had no authoritative
measurement stamp; Grok and Kimi default sources were absent. Integration can
improve Codex with its supported existing-daemon read. These are source coverage
observations, not public account/allowance values.

## Signed banked or behind time

For a verified fixed-duration quota model, let `u` be the observed used fraction,
`start` the declared start or the modeled `reset-duration`, and `observedAt` the
quota observation time:

```text
signedSeconds = (observedAt-start)/1000 - u*(reset-start)/1000
```

Positive means banked allowance pacing credit; negative means behind; exact zero
means on pace. This matches the inspected Burn Bar `paceLive()` arithmetic:
`bankedMs=(elapsed-used)*windowMs`, and behind recovery at
`reset-windowMs*(1-used)`. The reader does not copy Burn Bar's grace thresholds or
its approximate 99.5%-spent rule. It preserves the actual fraction and labels
the result **pace-equivalent allowance credit**. It is not guaranteed compute
time, agent progress, transferable credit, or a promise that a provider will
unblock a request.

The signed headline remains anchored to the source observation. Conditional
recovery is `start + u*(reset-start)`; remaining wait is that timestamp minus
the current clock, bounded at zero. The UI explicitly says **if no additional
usage**, shows the observation time, and displays recovery using the actual
desktop local date/time and the UTC offset applicable at recovery. The date is
always included, so midnight and DST changes are unambiguous. It does not guess
the user's timezone or print a UTC timestamp as though it were local time.
Recovery and rate-limit reset remain separate fields. Rolling or unknown windows
withhold time credit and wait. After reset, a new source observation is required.

## Bounded reader and UI contract

The reader allows only regular user-owned JSON files, rejects symlink targets,
reads at most 64 KiB per file, bounds nesting and list sizes, and displays at most
eight quota windows with an explicit overflow count. Unknown fractions, booleans
masquerading as numbers, missing stamps, and observations older than 15 minutes
produce unavailable or stale results, never measured zero. Zero is displayed
only when the source actually supplies it. A file's mtime or `updatedAt` is not
used as a replacement quota observation stamp. The most behind usable window is
the record's primary metric; every retained window is separately selectable.

```text
collect() -> {schema:1, observedAt:epochMs, providers:[record, ...]}
record -> {provider,id,metric,windows,overflowCount,ordinaryUsageAllowed:boolean|null}
metric -> {state,freshness,unit,allowanceUsed,allowanceRemaining,
           source,observedAt,resetAt,label,pace}
pace -> {state,signedSeconds,meaning,source,formula,fixedWindow,
         windowStartAt,windowBasis,recoveryAt,waitSeconds,assumption}
```

`record(provider, document, source=..., now_ms=..., measured_at=...)` is the
normalization API for supported integration reads. `normalize_window()` accepts
`{label, percent, resetsAt, durationMs?, startsAt?, windowKind?}`. Explicit duration
is a positive integer number of milliseconds, at most 366 days. `windowKind:
"rolling"` disables fixed-window time estimates.

The QML component accepts `city`, `records`, `agents`, `activeProvider` and emits
`providerSelected(provider)`, `closed()` and `refreshRequested()`. Reset emits
`providerSelected("")`. The integration owns provider toggling and any refresh.
Counts use actual supplied session metadata; reported workflow states require
fresh live adapter source/time evidence. Stored sessions are not assumed active.
The provider identity markers use four distinct colors; pacing headlines use the
host's theme accent/ink with explicit text, not provider colors as status.

The component was checked offscreen at 560×460 and 900×460 logical pixels,
including full pages, controls, stale/unknown states, multi-window selection and
footer separation. Native monitor scaling and integrated city/desk filtering
remain integration checks.

## Reference inspection and licensing

Reference designs inspected: Infomarchy 1.4.1 (`InfoModel.qml`, `InfoView.qml`,
`collector.ts`, `ai-ops.ts`) and [Burn Bar](https://github.com/nixfred/burnbar) 2.2.4
(`Service.qml`, `BarWidget.qml` `paceLive/standingAt`, `BurnPanel.qml`, and
`bin/burnbar-collect` `limits_for/probe_measured_at/kimi_limits_from_usages`).
Both installed references carry MIT licenses (Infomarchy copyright Fred Nix;
Burn Bar copyright nixfred). Omarchy's inspected Claude/Codex usage producer
helpers are also MIT licensed. The new collector, display model and components
are independently written; no source code from those projects was copied and
no installed-source runtime import was added.

The Codex reader considers all valid unique windows within its bounded daemon response, ranks the most behind first, then applies the eight-window display cap with an explicit overflow count. It does not silently discard later quota buckets.
