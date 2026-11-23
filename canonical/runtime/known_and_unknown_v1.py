"""What do I know, and what don't I? One answer, assembled from what is measured, not from statuses.

THE QUESTION THE OWNER ASKED, LITERALLY:

    "All the agent should do is scan everything in the environment and then retrieve from his memory
     what he knows and what he doesn't know. What he doesn't know, he should get it instantly."

Two modules already answer half of that sentence each, and NOTHING CONNECTS THEM:

  * `capability_type_surface_v1.unknowns()` — for each capability, the slots whose TYPE could not be
    derived. Measured 2026-11-23: it has exactly one caller in the whole tree, a test asserting it
    returns `{}`. It is dead code.
  * `reachability_v2` — for each claim, whether it can be called, and which slots cannot be filled
    from real values in this tree (`NEEDS_INPUT:<slot>`).

They are not the same question and they were being read as if they were. Measured, four rows disagree
outright:

    git.repository.operate.v1     surface: message, op, rev, staged, target
                                  reachability adds: repo_root, limit
    code.patch.tree_sitter.verify.v1  surface: edits, test_cwd
                                  reachability adds: selection_path

`repo_root` is typed `PATH_DIR` and is not "unknown"; it is simply not filled by the audit's argument
builder. So `unknowns()` reported a *smaller* gap than existed and a reader would conclude the machine
knew more than it did. Two answers implemented twice drift — this project's own recorded lesson, met again.

WHAT THIS FILE DOES. It asks the two sources the questions they can actually answer and composes one
statement per capability, with four distinct states, because the next action differs:

    DO          it ran here and produced something that can be read back
    SELF_ATTESTING  it ran, takes no input, and restated the registry -- reachable, not informative
    TYPED_OUT   it did not run, and its slots are understood; the audit simply could not fill them
    UNTYPED     a slot's type could not be derived -- the machine would not recognise a correct value
    UNDECLARED  it names nothing that can be looked up (no adapter, no tool, no module)

THE POINT OF SEPARATING THEM is the same point as A84 and A85: `UNREACHABLE` was one word for a broken
file, a missing tool, and a wheel for another Python. `UNKNOWN` would be one word for "I need a path" and
"I do not know what a path is here" — and only the second one requires learning something.

It re-uses both modules rather than re-deriving either. The only new thing is the composition and the
rule for what the states mean, which is the smallest possible part.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_KNOWN_AND_UNKNOWN_V1"

_RAN = frozenset({"WROTE", "RAN"})
_REFUSED = frozenset({"LOADED"})


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def known_and_unknown(reg: Mapping[str, Mapping[str, Any]] | None = None,
                      root: pathlib.Path | None = None) -> dict[str, Any]:
    """One statement per claiming capability: can it run, and if not, what exactly is missing."""
    from canonical.runtime import capability_type_surface_v1 as surface
    from canonical.runtime import live_integrated_brain_v1 as brain
    from canonical.runtime import reachability_v2 as reach

    reg = reg if reg is not None else brain.load_verified_registry()
    root = pathlib.Path(root or _root()).resolve()
    census = reach.reachability(reg=reg, root=root)
    untyped = surface.unknowns(reg)

    rows: dict[str, Any] = {}
    for cid, cell in census["cells"].items():
        state = cell["state"]
        if state == "SELF_ATTESTING":
            # IT RAN AND IT MEASURED NOTHING. Folding this into DO would count a restatement of the
            # registry as knowledge, which is the exact defect A84 found in 19 rows. It must stay
            # visible as its own state.
            rows[cid] = {"state": "SELF_ATTESTING", "why": cell.get("why"),
                         "evidence": "ran with no input, so its verdict is about itself"}
            continue
        if state in _RAN:
            rows[cid] = {"state": "DO", "evidence": cell.get("artifact") or "ran, nothing to read back"}
            continue
        if state in _REFUSED:
            # A refusal is an answer: the call reached the code and the code declined. That is knowledge.
            rows[cid] = {"state": "REFUSES", "why": cell.get("why"), "detail": cell.get("detail")}
            continue
        why = str(cell.get("why") or "")
        tool = cell.get("tool") or {}
        if why.startswith("NO_ADAPTER_DECLARED"):
            rows[cid] = {"state": "UNDECLARED", "why": why, "tool": tool}
            continue
        if why.startswith("NEEDS_INPUT:"):
            missing = [s for s in why.split(":", 1)[1].split(",") if s]
            rows[cid] = {"state": "TYPED_OUT", "missing": missing,
                         "untyped_slots": untyped.get(cid, []),
                         "why": "THE_VALUES_IT_WANTS_ARE_NOT_IN_THIS_TREE"}
            # A slot that is BOTH unfilled and untyped is the harder case and must not hide behind the
            # easier one: the audit cannot produce a value AND the machine would not know a good one.
            if untyped.get(cid):
                rows[cid]["state"] = "UNTYPED"
                rows[cid]["why"] = "A_SLOT_IT_NEEDS_HAS_NO_DERIVABLE_TYPE"
            continue
        rows[cid] = {"state": "UNREACHABLE", "why": why, "detail": cell.get("detail")}

    # A capability whose types are unknown but which the census never planned needs saying too.
    for cid, slots in untyped.items():
        if cid not in rows and cid in census["cells"]:
            rows[cid] = {"state": "UNTYPED", "untyped_slots": slots,
                         "why": "A_SLOT_IT_NEEDS_HAS_NO_DERIVABLE_TYPE"}

    counts: dict[str, int] = {}
    for row in rows.values():
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return {"schema": SCHEMA, "claims": len(rows), "counts": counts, "rows": rows,
            "world": census["world"], "interpreter": census["interpreter"],
            "note": ("DO is measured by running. TYPED_OUT needs a value from somewhere other than this "
                     "tree; UNTYPED needs a value AND a way to recognise one; UNDECLARED needs a binding.")}


def main() -> None:
    report = known_and_unknown()
    print(json.dumps({"claims": report["claims"], "counts": report["counts"],
                      "world": report["world"]}, indent=1))
    for cid, row in sorted(report["rows"].items()):
        detail = (row.get("missing") or row.get("untyped_slots") or row.get("why") or "")
        print("  %-46s %-11s %s" % (cid[:46], row["state"], str(detail)[:70]))


if __name__ == "__main__":
    main()
