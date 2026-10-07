# Source review record

## Historical 2.2 review

An independent live Kimi K3 source audit informed the original 2.2 release. Accepted fixes covered editable inactive app rules, stable color-only changes, correct group-heading hits, one edit per CLI call and monotonic classification settling. The runtime also received native fixture checks. Original detailed review inputs, responses and decisions were retained privately; this attribution does not establish review of later source changes.

## 3.0 review

An actual independent Grok source review completed against integration snapshot `dfa2f204478b9493b5e74054c0d0fb542d930d1b`. The service returned **grok-4.7-build**, with a normal stop, two messages and no tools. It inspected source only; it did not run tests or observe a desktop. The review found blockers and was not a passing release audit.

Validated corrections cover draft character order and uncertain submission IDs, explicit reply reads, stale helper responses, process-start identity, partial organization receipts, post-move observation, protected districts, Qt JSON signature transport, inventory bounds, provider explanations and consistent versioning. Additional local review reproduced and corrected session-switch deferred edits, historical raw-source rendering, provider/family identity collisions and malformed queue acknowledgements. Pending submission IDs remain bound to exact drafts and cannot be silently evicted at capacity.

The corrected candidate was independently inspected locally at integration snapshot `63033968265c6795eeb7be1f588874c434a6b45c`, with runtime Git tree `b56c63d6af59b71cf9e082ac82610f3fdbb69769`. The local reviewer identified no remaining concrete blocker in the reviewed paths and independently ran adapter and view-identity checks plus all runtime byte comparisons. Other portable and native results are owner-executed evidence, listed in the [verification record](../verification/RELEASE.json).

**At that frozen snapshot, the corrected-source Grok follow-up had not run.** This record establishes the initial external review and a corrected local assessment. Local review is not described as a final Grok pass. Publication and installation status must be established by their own exact-commit CI and installation receipts, independently of this source assessment.

Raw review prompts, responses, credentials, local diagnostics and real user content are retained privately and are not published. Native interaction fixtures use synthetic data. No real user session instruction was sent; recognized protocol methods and mock queue handling do not establish actual provider delivery. Live visible native interaction remains separate from hidden installed-backend geometry checks.

## Multi-provider extension

The extension adds Claude stored subagents, native Grok tagged assistant history, Pi/Kimi3 saved sessions, a shared Agent Desk, and standalone quota pacing. A focused local review found and corrected Claude path/mode/hardlink safety, bounded selected lookup, Grok native record discriminators and aggregate capabilities, and stale A→B→A reply acceptance. The reviewer independently reproduced the corrected guards with fixtures and ran 77 provider plus 27 session tests. No remaining concrete blocker was found in those corrected paths; this is not broad release clearance or an external Grok pass.

The [extension evidence](../verification/EXTENSION.json) binds the new runtime hashes and owner-executed tests to their source snapshot. The original frozen release evidence remains separate. Subsequent external review and local finding dispositions are recorded below. Publication, exact published-commit CI, installation and live visible QA are separate gates.

## Final external extension audit

After explicit source-disclosure approval, the exact 47 sanitized source/test/documentation files (516,715 source bytes) from `09ec9333ecb275f000c3fa123ddb778fde4a6135` were submitted once to Grok/xAI. The response identified **grok-4.7-build**, stopped normally, and reported **no concrete release blocker** with three nonblocking medium findings. It performed source review only, with no tools or claimed test execution. Prompt SHA-256: `b3dac3347e50b7894a5fca2059cc3e51b9f0b54067cde342f510acf9d5870ad4`. Raw prompts/responses remain private.

- **Later Codex quota buckets:** validated and corrected locally. The reader now considers every valid unique window within the bounded daemon response, keeps the most-behind windows before the eight-row display cap, and reports overflow. A regression puts the worst window in the ninth bucket.
- **Same-ID reply navigation:** did not reproduce in actual Qt. The existing metadata-refresh test and an additional test preserve both an older-response index and its text-page index after same-ID metadata replacement. The history binding depends on the unchanged boolean `replyMatchesSelection`, rather than rebuilding directly on the replacement session object. Production code was retained.
- **Monotonic clock reset:** rejected as an incorrect premise. Python's [documented monotonic clock](https://docs.python.org/3/library/time.html#time.monotonic) is shared across processes. Three fresh helper processes on the target returned ordered values inside the parent's monotonic interval. Group settling uses that host clock; helper restarts do not reset it. Production code was retained.

The quota correction was regression checked locally after the external response; the corrected source was not uploaded for a second external review. The release evidence binds the final runtime and local checks separately from the externally audited source snapshot. No real user-session instruction was sent. Native fixture QA does not establish live visible user QA.
