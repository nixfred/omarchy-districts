# Local session adapter contract

Districts' automatic inventory contains provider/session IDs, explicit ancestry,
reported state, availability and capability reasons. It omits titles, prompts,
replies, paths and PID guesses. Agent courts represent sessions, not OS windows.
No monitor/workspace ownership is inferred. Generic Codex guardian/compaction
helpers are not rendered as invented semantic subagents.

## CLI integration

Run with the current Python interpreter and this runtime's `sessions.py` path.
Every operation prints one JSON result; `ok:false` exits 1. Never log stdin,
reply JSON or raw provider bodies. The session adapter owns one bounded process at a time; quota metadata uses a separate read-only process.

- `inventory`: metadata-only local inventory; bound 128 records, `bounded:true`
  when recent inventory has more. Codex loaded threads plus recent interactive
  records and explicit recorded spawn children; Claude live agents JSON and native subagent metadata; Grok summaries/explicit child sidecars; Pi headers/model changes. Provider groups share the cap fairly.
- `reply --provider codex|claude|grok|pi --id ID`: opt-in selected-session reply.
  Codex CLI first tries up to 64 recent items; on method-not-found it uses
  `thread/turns/list` with at most 4 full turns. If both paginated methods are
  unavailable, it uses selected `thread/read` with `includeTurns:true`, still
  enforcing the 8MiB transport/history bound. It selects the latest
  non-commentary assistant message and includes reported turn status. Claude accepts its UUID or exact `mainUUID:agentID` identity; Grok accepts its native UUID and Pi its validated opaque ID. Stored providers read only the exact selected bounded transcript tail. All return recent assistant-only history; reasoning, tools and user text stay excluded.
  History is capped at 16 assistant messages and 65,536 shared characters, with explicit truncation indications.
- `metrics`: optional stamped local quota snapshots plus existing Codex daemon's `account/rateLimits/read {}`. No tokens, model calls or permission writes.
- `send --provider codex --id UUID --message-id UUID`: write exactly one JSON
  line to stdin: `{"text":"User's exact instruction"}\n`. Bounded `readline`
  permits Quickshell Process.write without closing stdin. Maximum 8,192 text
  characters. Capture target/draft/message ID before starting the process.
- `open`: currently returns unavailable. An exact native-client route for these
  CLI daemon threads has not been proven. A registered `codex://` handler does
  not prove that a separate desktop app owns the same CLI thread.

Example record (fixture IDs):

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "provider": "codex",
  "key": "agent:codex:22222222-2222-4222-8222-222222222222",
  "parentId": "11111111-1111-4111-8111-111111111111",
  "familyId": "11111111-1111-4111-8111-111111111111",
  "label": "Codex CLI 22222222",
  "status": {"type": "notLoaded", "activeFlags": []},
  "statusSource": "Codex CLI daemon thread/read",
  "parentSource": "Codex stored SessionSource.thread_spawn",
  "availability": "stored",
  "observedAt": "2026-01-01T00:00:00Z",
  "capabilities": {
    "canReadReply": true,
    "canSend": false,
    "canOpen": false,
    "approvalPolicy": "existing-session-unchanged",
    "approvalPending": false,
    "reason": "Only a loaded thread accepting direct input can receive instructions."
  }
}
```

Ancestry comes from API `parentThreadId`, declared `SessionSource.thread_spawn`,
or `thread_spawn_edges` in Codex's existing state DB, opened read-only. Family
IDs follow those explicit edges; cycles are rejected. An open stored spawn edge
is not evidence of a running child. Status is the provider's reported state,
never a task progress percentage. Codex states: `idle`, `active`, `notLoaded`,
`systemError`; active flags `waitingOnApproval`, `waitingOnUserInput`. Claude's
reported state string remains as supplied and has no inferred parent link.

## Exact transport and approval behavior

The installed Codex 0.160.1 generated schema and official
[app-server protocol](https://developers.openai.com/codex/app-server) define the
local Unix socket as WebSocket with HTTP Upgrade and one JSON-RPC message per
text frame. Districts connects only to the existing owner-only control socket;
it validates its handshake and bounds frames/time. No daemon start, thread
resume, competing model process, auth fallback or config change occurs.

Immediately before sending, read the loaded-thread list and exact metadata.
Require matching UUID, `canAcceptDirectInput:true`, idle/active status and no
blocking flags. Submit only `thread/queue/add` with exact native thread ID,
user-generated text and retained `clientUserMessageId`. No approval/sandbox,
model, hook, system prompt or filesystem policy fields are sent. Districts never
answers server approval/question requests; the existing owning client retains
those requests. A queue receipt means queued, not executed or completed. On
uncertain connection loss, preserve the draft and message identity; never
retry automatically. Fresh inventory/reply or the native client is the recovery
path. Replay mode must block sends and restore a fresh live selection first.

Other providers:

| Provider | Inventory/reply | Existing-session instructions |
|---|---|---|
| Codex CLI daemon | Live/stored metadata, explicit children, selected reply | Exact loaded-thread queue |
| Claude | Live main metadata, stored subagents and selected assistant history; immediate parent unknown | Disabled: same-process write API unverified |
| Herdr | Not inspected live by this outside-Herdr application | Disabled: installed skill requires `HERDR_ENV=1` |
| Kimi | Pi model metadata recognizes saved Kimi3 sessions; no saved session is fabricated from model configuration | Disabled: ACP starts its own protocol process |
| Pi | Saved session/model metadata and selected persisted-branch assistant history; fork is not a subagent | Disabled: RPC belongs to its owning process |
| Grok | Stored summary metadata, explicit child links and selected native tagged assistant history; live state unknown | Disabled: existing-process transport unverified |

No terminal input injection or resume-as-attach fallback is implemented.

## AgentV2 component

Explicit properties: `city` (theme object), `selectedAgent`, `reply`, `draft`,
`busy`, `message`, `availableAgents`, `providerFilter`, `replyIdentity`. Signals: `requestSelect(agent)`, `requestRead(agent)`,
`requestSend(agent,text,messageId)`, `requestOpen(agent)`, `draftEdited(text)`,
`closed()`. The parent owns CLI processes and per-session drafts. Freeze the
selected context while any request runs. Discard late reply results if their
provider/ID, UI generation or selection epoch no longer matches the shared Desk. A→B→A selection cannot accept an earlier A response; same-ID metadata refresh preserves the epoch. Do not clear an uncertain
send draft or automatically resubmit it.

Reply and instruction use explicit pages, plain text and a monospace font,
measured conservatively against the actual content boxes. Reply and instruction views share one desk with separate response and text pages. Sending has
an exact-session review step. Provider unavailable/blocking reasons remain
visible. No scroller or hidden history subscription is used.

## Verification scope

The Python cases include a real isolated Unix WebSocket protocol fixture,
fragmented messages/interleaved ping, exact-ID queue fields, approval requests
never answered, invalid handshake and non-owner-only socket rejection, selected
reply privacy and explicit ancestry. Live metadata-only inventory was checked separately. Counts are machine-specific and are not release evidence.

Offscreen Qt checks cover long-paste reflow/limit preservation, paged reply/draft fit at 912×512, 1600×900 and
2560×1440; complete draft signal/review and blocked send controls. This is
fixture QA, not live provider prompt delivery or native visible click QA. No
instruction was sent to existing user agents. The queue protocol was exercised
only against the controlled mock provider. The independent source audit and its exact targets are recorded in [review/README.md](review/README.md).

Pending review and queue identities are retained with their exact drafts in RAM. Switching sessions, inventory refresh, panel close and historical views never evict a pending identity. At sixteen retained identities, preparing a new one stops with a visible explanation; the existing identity can still be reviewed. Explicitly editing its draft releases the previous identity. Ordinary draft caching is separately bounded, and no draft or submission text is persisted.

## Running daemon compatibility and desktop boundary

Generated CLI schemas are an available-method reference, not proof of the
running daemon's method set. Harmless nonexistent fixture-ID probes against the running daemon
confirmed `thread/items/list` returns method-not-found (-32601), while
`thread/turns/list` and `thread/read` are recognized and reject the nonexistent
thread (-32600). `thread/queue/add` is recognized and rejects the empty-input,
nonexistent target (-32603). No real session content or instruction was used.
Fallback occurs only on method-not-found; invalid IDs/provider errors are not
retried through another read route. Queue execution against a real provider
remains untested; exact wire behavior is covered by the isolated fixture.

All Codex labels explicitly say **Codex CLI** and carry
`sessionScope:local-cli-daemon`. These records do not establish the identities
or status of current ChatGPT/Codex desktop worktree tasks. Official
[developer documentation](https://learn.chatgpt.com/docs/developers) and
[app-server documentation](https://learn.chatgpt.com/docs/app-server) establish
the app-server integration, but no published supported external runtime API for
this installed desktop task namespace was found. The locally bundled Codex app
tools are agent-session tools, not a documented external plugin endpoint. No
private Electron RPC, token extraction, terminal injection, or resume process
is used to cross that boundary. The inventory includes an explicit
`codex-desktop` unavailable reason. Desktop task integration remains a real
limitation requiring an officially supported bridge.
