# Development

This directory is the complete Districts source project. It can be copied or
cloned to another location without the original development task directory.
It uses Omarchy's installed shell imports at runtime; it does not depend on
Mycelium or Infomarchy.

## Source layout

| Path | Purpose |
| --- | --- |
| `manifest.json` | Plugin identity and versioned entry point |
| `v2.2/` | Production QML, JavaScript and Python runtime |
| Root QML/JS/Python copies | Test harness inputs; keep identical to `v2.2/` |
| `install.py` | Validated 14-file staging and optional scoped activation |
| `tests/` | Portable bridge/model checks and native synthetic fixtures |
| `docs/images/` | Original hero and sanitized native screenshots |
| `tools/check-project.py` | Release completeness, runtime parity and local link checks |

There is no compilation or bundle step: Quickshell loads the QML and
JavaScript, and Python runs the bridge with its standard library. Python 3.10+
and Node.js 18+ are sufficient for portable checks.

## Portable checks

Run from the project root:

```bash
python3 tools/check-project.py
python3 -m unittest discover -s tests -p 'test_bridge.py'
node tests/model.js
node tests/camera.js
node tests/groups.js
```

These checks use project-relative source paths and disposable fixture data.
They do not need a live desktop. Root/runtime parity must pass before staging.

## Native fixtures

The native fixtures require Quickshell, QtTest, an awake Omarchy Wayland
session and `OMARCHY_PATH` pointing to the Omarchy installation or checkout
that provides `shell/Commons`, `shell/Ui` and `shell/services`.

```bash
python3 tests/grouping.py
python3 tests/pagination.py
python3 tests/interaction.py
```

These fixtures draw their own synthetic surfaces with keyboard focus disabled
and pointer input excluded from the real desktop. Simulated control actions
remain inside the fixture. They use temporary state and scoped child processes;
they neither activate the plugin nor move real windows. Logs and captures go to
ignored `verification/`. Use a copied source tree for a fresh verification run
when preserving existing local evidence.

`tests/activation_health.py` is a historical installation diagnostic, not a
general checkout test. It expects the private `vic-v2-installation.json` receipt
and its original backup. Those records are intentionally excluded from public
source. `tests/live_bridge.py` inspects the actual desktop and should only be
used for an explicitly requested live diagnostic. `tests/docs_capture.py`
regenerates public image assets using six representative neighborhoods with short, sanitized names. Keep crowded stress fixtures and repeated long labels in private verification output; they are not showcase images. The capture script is not part of ordinary verification.

## Stage or install

See the [installation instructions](../README.md#install-on-an-existing-omarchy-desktop).
For a non-live staging check, choose an empty temporary destination and an
explicit receipt path:

```bash
python3 install.py --destination /tmp/districts-preview/nixfred.districts \
  --receipt /tmp/districts-preview/installation.json
```

This copies and validates the runtime without enabling it. Live installation
uses `python3 install.py --enable` from a normal desktop session. Keep the
source checkout separate from the installed plugin directory. Retain private
receipts, backups and historical runtime artifacts locally.
