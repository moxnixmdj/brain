#!/usr/bin/env python3
"""SAFETY PROBE: the new filters must not make the machine LESS willing to fail closed.

F27 and F28 make the retrieval path read the request's own words more carefully, which
makes MORE sentences resolvable.  The risk is the opposite of a win: a request that names
nothing, or names the wrong thing, must still be REFUSED rather than answered by a
capability the request did not ask for.

This measures, over the out-of-scope sentences the heartbeat uses and over a set of
adversarial near-misses, that the entry still fails closed.

Read-only.  Writes /tmp/f27_fail_closed.json.  Authority: NONE.  Credit: 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

# Requests that name no capability at all, or name one in a way that must not resolve.
ADVERSARIAL = [
    "Do the needful thing.",
    "Run the thing.",
    "Run the v1.",
    "Run the canonical runtime py auto v1.",
    "Run the auto canonical runtime.",
    "Please handle it as usual.",
    "Run the.",
    "Run the v2.",
    "Do what is right.",
    "Run the capability.",
    "Run the 1.",
    "Run the v.",
    "Run the auto.",
    "Run the py auto v1 canonical runtime.",
]


def main() -> int:
    reg = gc._platform_admissible_registry(dict(load_verified_registry()))
    rows = []
    for goal in ADVERSARIAL:
        row: dict[str, object] = {"goal": goal}
        try:
            compiled = front.compile_goal(goal, reg, ROOT)
            row["compiled"] = compiled.get("selected_capability")
            row["mode"] = compiled.get("compiler_mode")
        except gc.GoalCompilationFailure as exc:
            row["compiled"] = None
            row["failure"] = exc.code
        result = solve({"task_id": "probe-failclosed-001", "goal": goal})
        row["pass"] = result.get("pass")
        row["status"] = str(result.get("status"))[:70]
        row["failed_closed"] = result.get("pass") is not True
        rows.append(row)
    Path("/tmp/f27_fail_closed.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    closed = sum(1 for r in rows if r["failed_closed"])
    print(f"adversarial requests that failed closed: {closed}/{len(rows)}")
    for r in rows:
        mark = "OK " if r["failed_closed"] else "!! "
        print(f" {mark}{r['goal'][:52]:<52} pass={r['pass']} status={r['status'][:46]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
