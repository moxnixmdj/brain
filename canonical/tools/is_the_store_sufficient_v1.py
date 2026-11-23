#!/usr/bin/env python3
"""Is the saved form SUFFICIENT, or merely small?

The user's requirement, in their own words:

    "Saving his exact experience must be in a very sufficient way, not just saving the exact
     experience in a dumb way."

Small is easy. `ask_the_host_the_right_question_v1` got a host's memory to 8,240 bytes. The
question that matters is the opposite one: **can a machine that has never run here rebuild the
whole answer from that store plus a fresh scan?** If it cannot, the store is small and useless.

THE TEST, AND WHY IT IS THE RIGHT ONE
-------------------------------------
Take a host. Build the store by asking every program. Then, in a FRESH PROCESS with ONLY the
store and the host:

    rebuild  = scan(host) + store   ->  answers

and compare against the answers the asking pass produced. Three things must hold:

  SOUND      every answer in `rebuild` is in `answers`          (no invention)
  COMPLETE   every answer in `answers` is in `rebuild`          (no loss)
  CHEAP      rebuild spends no probe on anything already read

If SOUND and COMPLETE both hold, the store is a faithful, sufficient summary of the pass. If
COMPLETE fails, the store dropped something. If SOUND fails, it invented something -- which is
worse, because an invented answer is indistinguishable from a measured one until it is used.

WHY A FRESH PROCESS AND NOT A FUNCTION CALL
-------------------------------------------
A function-call round trip can pass state through a live Python object that a restarted machine
would not have; that is the same error as a cache that only works warm. The rebuild reads the
JSON file from disk.

Authority: NONE. Producer-run sandbox measurement. Zero model calls, zero network at run time.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SCHEMA = "BRAIN_IS_THE_STORE_SUFFICIENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

REBUILD = r'''
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import ask_the_host_the_right_question_v1 as A
host = pathlib.Path(sys.argv[2]); mem = pathlib.Path(sys.argv[3])
roles = json.loads(sys.argv[4])
rows = A.scan(host)
out = {"from_memory": {}, "had_to_ask": {}, "memory_bytes": mem.stat().st_size}
for role in roles:
    got = {}
    had = 0
    for row in rows:
        state, flag = A.known_answer(A.load(mem), row, role)
        if state == A.PRESENT:
            got[row["name"]] = flag
        elif state == A.UNREADABLE:
            had += 1
    out["from_memory"][role] = got
    out["had_to_ask"][role] = had
print("@@@" + json.dumps(out))
'''


def build_store(host: pathlib.Path, roles: list[str], store: pathlib.Path) -> dict[str, Any]:
    import ask_the_host_the_right_question_v1 as A

    if store.exists():
        store.unlink()
    return A.resolve(host, roles, memory_path=store)


def rebuild_from(host: pathlib.Path, roles: list[str], store: pathlib.Path) -> dict[str, Any]:
    """A fresh process, the store, and the host. Nothing else."""
    tools = str(pathlib.Path(__file__).resolve().parent)
    proc = subprocess.run([sys.executable, "-c", REBUILD, tools, str(host), str(store),
                           json.dumps(roles)],
                          capture_output=True, text=True, timeout=900)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("@@@"):
            return json.loads(line[3:])
    raise RuntimeError("rebuild failed: " + (proc.stderr or "")[-400:])


def compare(host: pathlib.Path, roles: list[str], *,
            store: pathlib.Path | None = None) -> dict[str, Any]:
    store = store or pathlib.Path(tempfile.mkdtemp(prefix="sufficient-")) / "store.json"
    built = build_store(host, roles, store)
    rebuilt = rebuild_from(host, roles, store)
    reported = {role: dict(built["roles"][role]["programs"]) for role in roles}
    from_mem = {role: dict(rebuilt["from_memory"].get(role) or {}) for role in roles}

    sound, complete, missing = {}, {}, {}
    for role in roles:
        a, b = reported[role], from_mem[role]
        invented = {k: v for k, v in b.items() if a.get(k) != v}
        lost = {k: v for k, v in a.items() if b.get(k) != v}
        sound[role] = not invented
        complete[role] = not lost
        if invented:
            missing.setdefault("invented", {})[role] = invented
        if lost:
            missing.setdefault("lost", {})[role] = lost

    return {
        "schema": SCHEMA, "authority": AUTHORITY, "host": str(host),
        "roles": roles,
        "answers_reported": sum(len(v) for v in reported.values()),
        "answers_rebuilt": sum(len(v) for v in from_mem.values()),
        "sound": all(sound.values()),
        "complete": all(complete.values()),
        "per_role": {role: {"sound": sound[role], "complete": complete[role],
                            "reported": len(reported[role]),
                            "rebuilt": len(from_mem[role])} for role in roles},
        "had_to_ask_at_rebuild": rebuilt["had_to_ask"],
        "store_bytes": rebuilt["memory_bytes"],
        "discrepancies": missing,
        "verdict": ("SUFFICIENT" if all(sound.values()) and all(complete.values())
                    else "NOT SUFFICIENT"),
        "cost_zeros": {"model_calls": 0, "network_calls": 0, "parameters_stored": 0},
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="/usr/bin")
    parser.add_argument("--roles", nargs="*", default=["decompress", "compress", "stdout"])
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = compare(pathlib.Path(args.host), args.roles)
    print(json.dumps({k: report[k] for k in
                      ("host", "answers_reported", "answers_rebuilt", "sound", "complete",
                       "verdict", "store_bytes", "per_role", "discrepancies")}, indent=1))
    return 0 if report["verdict"] == "SUFFICIENT" else 1


if __name__ == "__main__":
    sys.exit(main())
