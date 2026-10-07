#!/usr/bin/env python3
"""Read bounded, optional shared quota metadata. No auth, networking or transcript reads."""
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import stat
import time

PROVIDERS = ("grok", "claude", "codex", "kimi")
MAX_BYTES = 65536
MAX_WINDOWS = 8
FRESH_MS = 15 * 60 * 1000
MEANING = "pace-equivalent allowance credit"
FORMULA = "signedSeconds=(observedAt-windowStartAt)/1000-allowanceUsed*(resetAt-windowStartAt)/1000"


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def timestamp(value):
    if number(value) is not None:
        return int(value) if 0 < value < 2**53 else None
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return int(parsed.timestamp() * 1000)
    except (ValueError, OverflowError, OSError):
        return None


def read_metadata(path):
    """Only regular user-owned files, no symlink targets, bounded bytes and JSON depth."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_size > MAX_BYTES:
                return None
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return None
        value = json.loads(data)
        def bounded(item, depth=0):
            if depth > 8:
                return False
            if isinstance(item, dict):
                return len(item) <= 256 and all(bounded(v, depth + 1) for v in item.values())
            if isinstance(item, list):
                return len(item) <= 1024 and all(bounded(v, depth + 1) for v in item)
            return True
        return value if isinstance(value, dict) and bounded(value) else None
    except (OSError, ValueError, RecursionError):
        return None


def unavailable(reason, state="unavailable"):
    return {"state": state, "freshness": "stale" if state == "stale" else "unknown",
            "reason": reason, "unit": "fraction", "allowanceUsed": None,
            "allowanceRemaining": None, "resetAt": None, "source": None,
            "observedAt": None, "pace": {"state": "unavailable", "signedSeconds": None,
            "meaning": MEANING, "source": None, "formula": None, "fixedWindow": False}}


def declared_window(row, reset):
    explicit = timestamp(row.get("startsAt"))
    if explicit and reset and explicit < reset:
        return explicit, "provider-declared start and reset"
    duration = number(row.get("durationMs"))
    if duration is not None and 0 < duration <= 366 * 86400000 and float(duration).is_integer():
        if reset:
            return reset - duration, "provider-declared duration/reset; even-pace model"
    # Only an explicitly stated duration carries a time-equivalent pace.
    # 'Weekly', 'Session', and 'Monthly' alone do not establish a fixed start.
    label = row.get("label")
    match = re.search(r"\(([1-9][0-9]{0,2})-(hour|day)\)", label, re.I) if isinstance(label, str) else None
    if match and reset:
        duration = int(match[1]) * (3600000 if match[2].lower() == "hour" else 86400000)
        if duration <= 366 * 86400000:
            return reset - duration, "provider-declared duration/reset; even-pace model"
    return None, None


def normalize_window(row, *, measured_at, source, now_ms):
    if not isinstance(row, dict):
        return unavailable("Invalid quota metadata")
    label = row.get("label")
    label = label if isinstance(label, str) and len(label) <= 80 else "Quota window"
    used, measured = number(row.get("percent")), timestamp(measured_at)
    if used is None or not 0 <= used <= 1:
        result = unavailable("Provider usage fraction unavailable")
    elif measured is None or measured > now_ms + 60000:
        result = unavailable("Quota observation timestamp not established")
    elif now_ms - measured > FRESH_MS:
        result = unavailable("Last quota observation is stale", "stale")
    else:
        reset = timestamp(row.get("resetsAt"))
        if reset and now_ms >= reset:
            result = unavailable("Quota window has reset; a new observation is required", "stale")
        else:
            result = {"state": "measured", "freshness": "fresh", "unit": "fraction",
                      "allowanceUsed": used, "allowanceRemaining": 1 - used,
                      "resetAt": reset, "observedAt": measured, "source": source,
                      "pace": {"state": "unavailable", "signedSeconds": None, "meaning": MEANING,
                               "source": source, "formula": None, "fixedWindow": False,
                               "reason": "A verified fixed window is unavailable"}}
            start, basis = declared_window(row, reset)
            if start is not None and start <= measured < reset and row.get("windowKind") != "rolling":
                credit = ((measured - start) - used * (reset - start)) / 1000
                target = start + used * (reset - start)
                result["pace"] = {"state": "banked" if credit > 0 else "behind" if credit < 0 else "on-pace",
                                  "signedSeconds": credit, "meaning": MEANING, "source": source,
                                  "formula": FORMULA, "fixedWindow": True, "windowBasis": basis,
                                  "windowStartAt": start, "observedAt": measured,
                                  "recoveryAt": target, "waitSeconds": max(0, (target - now_ms) / 1000),
                                  "assumption": "No additional usage since the quota observation",
                                  "allowanceExhausted": used == 1}
    result["label"] = label
    # Even unavailable/stale records carry the proven source stamp for explanation,
    # while their numeric usage/pace stays withheld.
    if source:
        result["source"] = source
    if measured:
        result["observedAt"] = measured
    return result


def record(provider, document, *, source, now_ms, measured_at=None):
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider")
    rows = document.get("limits") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not rows:
        windows = [unavailable("No supported quota metadata is available")]
    else:
        # A file's updatedAt/mtime is not proof that cached quota was remeasured.
        stamp = measured_at if measured_at is not None else document.get("limitsMeasuredAt", document.get("measuredAt", document.get("fetchedAtMs")))
        windows = [normalize_window(row, measured_at=stamp, source=source, now_ms=now_ms)
                   for row in rows[:MAX_WINDOWS] if isinstance(row, dict)]
        if not windows:
            windows = [unavailable("No supported quota metadata is available")]
    paced = [w for w in windows if number(w["pace"].get("signedSeconds")) is not None]
    measured = [w for w in windows if w["state"] == "measured"]
    primary = min(paced, key=lambda w: w["pace"]["signedSeconds"]) if paced else (measured or windows)[0]
    allowed = document.get("ordinaryUsageAllowed") if isinstance(document, dict) else None
    return {"id": "provider:" + provider, "provider": provider, "metric": primary,
            "ordinaryUsageAllowed": allowed if type(allowed) is bool else None,
            "windows": windows, "overflowCount": max(0, len(rows) - MAX_WINDOWS) if isinstance(rows, list) else 0}


def collect(*, state_root=None, cache_root=None, now_ms=None, reference_kimi=False):
    state_root = Path(state_root) if state_root is not None else Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    cache_root = Path(cache_root) if cache_root is not None else Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    records = []
    for provider in PROVIDERS:
        document = read_metadata(state_root / "omarchy/agents/usage" / (provider + ".json"))
        source = "Omarchy shared " + provider + " quota metadata"
        stamp = None
        if provider == "claude":
            probe = read_metadata(cache_root / "omarchy/agent-usage/claude-limits.json")
            if probe and isinstance(probe.get("limits"), list):
                document, stamp = probe, probe.get("fetchedAtMs")
                source = "Omarchy Claude quota probe cache"
        if provider == "kimi" and document is None and reference_kimi:
            document = read_metadata(state_root / "omarchy/burnbar/kimi-usage.json")
            source = "Explicit legacy Kimi quota snapshot import"
        records.append(record(provider, document, source=source, now_ms=now_ms, measured_at=stamp))
    return {"schema": 1, "observedAt": now_ms, "providers": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-kimi-cache", action="store_true", help="Explicit optional import of an existing plain Kimi quota snapshot; no plugin API")
    args = parser.parse_args()
    print(json.dumps(collect(reference_kimi=args.reference_kimi_cache), separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
