#!/usr/bin/env python3
"""On-demand counters for one compositor-verified window owner. No process tree."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

ADDRESS = re.compile(r"0x[0-9a-fA-F]{1,16}\Z")
READ_LIMIT = 65536
FD_LIMIT = 4096


class ResourceError(ValueError):
    """Only fixed, public messages may leave this helper."""



def positive(value, maximum=2147483647):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise ResourceError("Invalid process identity")
    return value


def read_bounded(path):
    with path.open("rb") as handle:
        data = handle.read(READ_LIMIT + 1)
    if len(data) > READ_LIMIT:
        raise ResourceError("Process counters exceed the read limit")
    return data.decode("utf-8", errors="replace")


def stat_counters(path, pid):
    raw = read_bounded(path)
    opening, closing = raw.find("("), raw.rfind(")")
    if opening < 1 or closing <= opening or raw[:opening].strip() != str(pid):
        raise ResourceError("Invalid process counters")
    fields = raw[closing + 1:].split()
    if len(fields) < 22:
        raise ResourceError("Incomplete process counters")
    values = [int(fields[i]) for i in (11, 12, 19)]
    if any(v < 0 for v in values) or values[2] == 0:
        raise ResourceError("Invalid process counters")
    # Never return the comm field: only fixed Linux counter fields leave /proc.
    return {"userTicks": values[0], "systemTicks": values[1], "startTime": values[2]}


def owner(clients, pid, address, app=None):
    if not isinstance(clients, list):
        raise ResourceError("Invalid compositor response")
    matches = [c for c in clients if isinstance(c, dict) and c.get("address") == address
               and c.get("mapped") is not False and c.get("hidden") is not True]
    if len(matches) != 1 or type(matches[0].get("pid")) is not int or matches[0]["pid"] != pid:
        raise ResourceError("Selected window owner changed; select it again")
    if app is not None and matches[0].get("class") != app:
        raise ResourceError("Selected app identity changed; select it again")
    return matches[0].get("class")


def inspect(pid, address, *, expected_start=None, app=None, query=None,
            proc_root=Path("/proc"), now=time.time, uid=None):
    """Dependency injection is test-only; the CLI always uses /proc and live IPC."""
    positive(pid)
    if not isinstance(address, str) or not ADDRESS.fullmatch(address):
        raise ResourceError("Invalid compositor window address")
    if expected_start is not None:
        positive(expected_start, 2**63 - 1)
    if app is not None and (not isinstance(app, str) or len(app) > 256):
        raise ResourceError("Invalid app identity")
    if query is None:
        from districts import query
    verified_app = owner(query("clients"), pid, address, app)
    directory = Path(proc_root) / str(pid)
    if directory.stat().st_uid != (os.getuid() if uid is None else uid):
        raise ResourceError("Owner process belongs to another user")
    counters = stat_counters(directory / "stat", pid)
    if expected_start is not None and counters["startTime"] != expected_start:
        raise ResourceError("Process identity changed; select the window again")
    facts = {"residentBytes": None, "virtualBytes": None, "threads": None,
             "fileDescriptors": None, "fileDescriptorsCapped": False}
    # Optional data may be inaccessible independently; core identity must still verify.
    try:
        for line in read_bounded(directory / "status").splitlines():
            match = re.fullmatch(r"(VmRSS|VmSize|Threads):\s+(\d+)(?:\s+(kB))?", line)
            if not match:
                continue
            key, number, unit = match.groups()
            if key == "Threads" and unit is None:
                facts["threads"] = int(number)
            elif key != "Threads" and unit == "kB":
                facts[{"VmRSS": "residentBytes", "VmSize": "virtualBytes"}[key]] = int(number) * 1024
    except (OSError, ValueError, UnicodeError):
        pass
    try:
        count = 0
        with os.scandir(directory / "fd") as descriptors:
            for _ in descriptors:
                count += 1
                if count > FD_LIMIT:
                    break
        facts["fileDescriptors"] = min(count, FD_LIMIT)
        facts["fileDescriptorsCapped"] = count > FD_LIMIT
    except OSError:
        pass
    after = stat_counters(directory / "stat", pid)
    if after["startTime"] != counters["startTime"]:
        raise ResourceError("Process identity changed during observation")
    owner(query("clients"), pid, address, verified_app)
    return {"ok": True, "schema": 1, "scope": "window-owner-process", "source": "linux-proc",
            "observedAt": round(now() * 1000), "pid": pid, "address": address,
            "startTime": counters["startTime"], "clockTicksPerSecond": os.sysconf("SC_CLK_TCK"),
            "userTicks": counters["userTicks"], "systemTicks": counters["systemTicks"], **facts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid", type=int)
    parser.add_argument("address")
    parser.add_argument("--start-time", type=int)
    parser.add_argument("--app")
    args = parser.parse_args()
    try:
        result = inspect(args.pid, args.address, expected_start=args.start_time, app=args.app)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        # Fixed messages only; no paths, private process names, or OS exception contents.
        message = str(error) if isinstance(error, ResourceError) else "Owner counters unavailable; refresh after selecting the window again"
        result = {"ok": False, "scope": "window-owner-process", "error": message}
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
