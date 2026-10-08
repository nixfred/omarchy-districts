# Local agent sessions

Districts displays provider metadata separately from app-window resource measurements. A terminal’s GUI PID is not proof of which agent is running inside it, and an agent court is not an invented compositor workspace. Parent/subagent edges require explicit provider spawn records. Unknown, stored-only and disconnected records stay labeled.

## Codex

The adapter targets an existing owner-only local Unix WebSocket app-server socket. It is supported only where the installed CLI’s required protocol methods are verified. The Codex desktop application’s distinct namespace is not interchangeable with that CLI API; unsupported namespaces do not gain sending capability merely because a socket exists.

Inventory reads bounded session metadata. **Read latest reply** requests assistant text from the exact selected thread. **Queue instruction** validates the full session UUID and checks that the session is still loaded before submitting through the verified queue method. It does not use resume, start a daemon or change sandbox/approval settings.

The native client continues to own approval prompts and user questions. Districts never answers server approval requests. The submission identity remains associated with an uncertain send; no automatic retry is allowed. An acknowledged queue item is labeled queued. It is not evidence that the agent started, obeyed or completed the instruction.

**Open native client** remains disabled until a supported exact route to the owning namespace is verified. A registered desktop URL handler alone does not prove that it can open CLI sessions.

## Claude

Claude inventory uses its supported read-only listing. An explicit reply request reads a bounded tail of that selected session’s stored assistant transcript. It is an excerpt from a stored record, not proof of current turn completion. Ambiguous or unsafe transcript paths are rejected.

Native stored subagent sidecars identify the owning main-session family and exact child ID. They do not establish the immediate spawning parent for nested children. These children remain marked as subagents without invented tree edges. No supported existing-process instruction API was verified. Sending and exact native opening stay unavailable; process ancestry supplies neither parentage nor progress.

## Grok

The installed CLI’s stored summaries identify sessions; an explicit matching child/parent sidecar can establish a subagent edge. Inventory reads metadata only. A selected reply read accepts the native tagged `type: assistant` records and returns bounded assistant-only history. Stored transcript text does not establish current execution or completion. No supported external instruction route to the existing interactive process was verified.

## Pi and Kimi3

Pi v3 session headers and explicit model-change metadata identify recorded sessions. Models `k3`, `k3-256k` and `kimi-for-coding` under `kimi-coding` are labeled Kimi3 while their exact provider transport remains Pi. A configured model is not a running or saved Kimi session. Fork ancestry is not subagent parentage. Selected history follows the last persisted branch; the current in-memory branch may differ.

Pi RPC owns a subprocess’s stdin/stdout; its in-process extension API requires an owner-loaded bridge. Districts does not launch either to attach to an existing session. Sending, live monitoring and native opening therefore remain unavailable.

## Other providers

Unavailable providers explain why a capability is missing. Districts does not launch ACP/RPC processes to simulate attachment to existing interactive sessions, restart agents, scrape terminal text, or inject keystrokes. Unsupported attachment remains a visible limitation.

## Shared Agent Desk

All buildings and the global control open one desk. Its provider-scoped selector includes stored records independently of the city’s stored-court setting. Session switches clear reply content before another result can appear. Replies must match the captured provider, exact session identity and current UI generation. Bounded recent assistant history uses response pages and text pages; older omitted entries are labeled. Metadata inventory is fair across available providers and capped at 128 records, with omissions reported.

## Content boundaries

Metadata inventory includes each session's real name where the provider records one: Codex thread name or agent nickname, Claude `agents --json` name or stored custom/agent/generated title records, Claude subagent type and description, Grok generated title or agent name, and Pi `/name`. Only explicit name/title fields are read, bounded to 64 visible characters with control and bidi characters removed; the working directory contributes its basename only. Prompts, message bodies, replies, full paths and PID guesses stay out. Reading a selected reply is opt-in and bounded. Displayed replies and drafts use plain text and pages. Instruction confirmation identifies the provider and exact session; replies, drafts and submission contents do not enter activity replay or saved camera state.

Fixture tests can establish protocol handling and guards. They cannot establish that a real user session accepted an instruction. Live sending is a user action and must be reported separately from mocked transport tests.
