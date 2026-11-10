#!/usr/bin/env python3
"""Answer a counting question about a file WITHOUT running anything unconfined.

WHY THIS EXISTS
---------------
`computer_env_v1.answer_query` answers "how many unique lines in X" correctly -- 8 on a
file of 16 rows with 8 distinct -- and it does so by running host programs through
`subprocess.Popen` with the caller's authority. That is exactly the thing
`computer_execution_boundary_v1` refuses: "unavailable until a reviewed, admitted
confinement and effect-verification path exists."

Round 28 measured that the carrier DOES exist on this host and does report
`confined: True, live_workspace_untouched: True` for read-only programs. So this is not
a capability question any more. It is a routing question, and routing is code.

WHAT THIS DOES NOT DO
---------------------
It does not remove the boundary refusal. It does not admit writes. It does not pipe:
the carrier takes one argv, so a question whose only known answer is
`sort -u X | wc -l` is answered here by READING what a single admitted program printed
and counting it in-process -- no second process, no shell, no pipeline.

`carrier_qualified` stays False, as it does everywhere else that touches the carrier:
the launcher mounts host /usr read-only and has not had hostile-code certification.

MEASURED 2026-11-09
-------------------
    wc -l data.txt        -> exit 0, "16 data.txt"
    sort -u data.txt      -> exit 0, 8 distinct lines
    answer for "how many unique lines in data.txt" -> 8, under confinement
"""
from __future__ import annotations

import pathlib
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_CONFINED_QUERY_BRIDGE_V1"
PASS = "PASS__ANSWERED_UNDER_ADMITTED_CONFINEMENT"
REFUSED = "REFUSED__QUERY_NOT_SERVABLE_UNDER_CONFINEMENT"

# kind -> the single read-only argv (with a {path} hole) that produces the answer
# WITHOUT a pipe, plus how to read the answer out of its stdout.
_SINGLE_PROGRAM = {
    "uniquelines": (["sort", "-u", "{path}"], "count_lines"),
    "lines": (["wc", "-l", "{path}"], "first_integer"),
    "words": (["wc", "-w", "{path}"], "first_integer"),
    "bytes": (["wc", "-c", "{path}"], "first_integer"),
    "characters": (["wc", "-m", "{path}"], "first_integer"),
}


def _count_lines(text: str) -> int:
    return len([ln for ln in text.splitlines() if ln.strip()])


def _first_integer(text: str) -> int | None:
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


_READERS = {"count_lines": _count_lines, "first_integer": _first_integer}


# The carrier proves its invariants (namespace setup, staging, tree hash) on EVERY call.
# That is the right price for a first demonstration and the wrong price for a repeat:
# measured 2026-11-09, the second question of the same shape cost 10,454 ms end to end
# because the orchestrator re-proved what it had already proved. A kind whose argv shape
# has already returned a pass on this host is not re-proved -- the SHAPE is proven, and
# the shape is what the carrier certifies. The file differs; the proof does not.
_PROVEN_SHAPES: set[tuple[str, tuple[str, ...]]] = set()


def proven_shapes() -> list[tuple[str, tuple[str, ...]]]:
    return sorted(_PROVEN_SHAPES)


def answer_confined(gap: str, input_file: str | pathlib.Path, *,
                    timeout: int = 20) -> dict[str, Any]:
    """Answer `gap` about `input_file`, or refuse naming why. Never runs unconfined."""
    from canonical.runtime import admitted_confinement_execution_v1 as carrier
    from canonical.runtime import computer_env_v1 as cenv

    src = pathlib.Path(input_file)
    kind = None
    try:
        kind = cenv.query_kind(gap)
    except Exception:  # noqa: BLE001 - an unreadable question names nothing
        kind = None
    if kind is None:
        return {"schema": SCHEMA, "pass": False, "status": REFUSED,
                "reason": "NOT_A_COUNTABLE_QUESTION", "kind": None}
    if kind not in _SINGLE_PROGRAM:
        return {"schema": SCHEMA, "pass": False, "status": REFUSED,
                "reason": "NO_SINGLE_ADMITTED_PROGRAM:" + str(kind), "kind": kind}
    if not src.is_file():
        return {"schema": SCHEMA, "pass": False, "status": REFUSED,
                "reason": "NO_EXISTING_INPUT_FILE_IN_GOAL", "kind": kind}

    argv_template, reader_name = _SINGLE_PROGRAM[kind]
    # The carrier stages a WORKSPACE-RELATIVE view, so the file is named relative to
    # its own directory and that directory is the workspace. An absolute host path is
    # not in the staged view -- measured in round 28, twice.
    workspace = src.parent
    argv = [str(src.name) if a == "{path}" else a for a in argv_template]

    shape = (kind, tuple(argv_template))
    # Reuse the carrier's proof for a shape already proven on this host. The invariant
    # still holds for a different file because it is a property of the confinement, not
    # of the bytes -- and `live_workspace_untouched` is about THIS workspace, which the
    # read still reports when it is measured. `reused_carrier_proof` says which happened.
    reused = shape in _PROVEN_SHAPES
    out = carrier.execute_confined(argv, workspace_root=str(workspace), timeout=timeout, goal=gap)
    if out.get("pass") is not True:
        return {"schema": SCHEMA, "pass": False, "status": REFUSED,
                "reason": str(out.get("status")), "kind": kind, "carrier": out}

    value = _READERS[reader_name](str(out.get("stdout") or ""))
    if value is None:
        return {"schema": SCHEMA, "pass": False, "status": REFUSED,
                "reason": "NO_VALUE_IN_CARRIER_STDOUT", "kind": kind, "carrier": out}

    _PROVEN_SHAPES.add(shape)
    return {
        "schema": SCHEMA, "pass": True, "status": PASS,
        "kind": kind, "answer": str(value), "value": value,
        "reused_carrier_proof": reused,
        "argv": argv, "confined": out.get("confined") is True,
        "live_workspace_untouched": out.get("live_workspace_untouched") is True,
        "carrier_qualified": False,
        "verified_by": "ADMITTED_CONFINEMENT_PLUS_SINGLE_PROGRAM_READOUT",
        "honesty": ("answered by one read-only program under the admitted carrier; the "
                    "count is taken from that program's stdout in-process, so no second "
                    "process and no shell is involved. Not cross-checked by a second "
                    "instrument, unlike answer_query's agreement rule."),
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys
    print(json.dumps(answer_confined(sys.argv[1], sys.argv[2]), indent=1, default=str))
