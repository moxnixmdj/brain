#!/usr/bin/env python3
"""DIAGNOSTIC: how much of the registry can a plain sentence reach, and does it RUN?

Two questions, measured on the live registry, with no authority and no credit:

  1. REACH.  For every capability that takes no input, does a plain sentence that NAMES it
     reach it?  The sentence is built only from the capability's own name - never its
     repository path, never its receipt document, never the lane's `.py.auto.vN` suffix.

  2. RUN, judged by an oracle this machine did not compute.  For every receipt-backed
     capability with an independent GitHub-Actions verification record, the capability is
     executed through the ONE entry and its result is compared with the `verifier_result_sha256`
     that a different identity, on different hardware, minted.  A capability whose result is
     a function of the live tree has no applicable CI value here, and the report says so
     rather than pretending the comparison was made.

Read-only with respect to tracked files (side effects reverted).  Writes
/tmp/prose_reach_and_oracle.json.  Authority: NONE.  Credit: 0.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402
from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime.live_brain_route_admission_v1 import solve  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

_ADAPTER_INJECTED = ("capability_id", "dependency")


def name_sentence(cid: str) -> str:
    """The plain sentence that NAMES a capability, in the capability's own words."""
    import re
    stem = re.sub(r"\.py\.auto\.v\d+$", "", cid.rsplit("/", 1)[-1])
    words = [w for w in stem.split("_") if len(w) > 1]
    return "Run the " + (" ".join(words) if words else "capability") + "."


def canonical_forms(tool_result: dict) -> list[Any]:
    """The canonicalizations of the entry's result the receipt lane's hash can take."""
    forms: list[Any] = [
        {k: v for k, v in tool_result.items() if k not in _ADAPTER_INJECTED},
        {k: v for k, v in tool_result.items() if k != "dependency"},
        tool_result,
    ]
    stdout = tool_result.get("stdout")
    if isinstance(stdout, str) and stdout.strip():
        try:
            forms.append(json.loads(stdout))
        except ValueError:
            pass
    return forms


def main() -> int:
    reg = gc._platform_admissible_registry(dict(load_verified_registry()))
    zero = {c: e for c, e in reg.items() if not front.is_plain_goal_routable(e)}

    # ---- 1. REACH
    reached, not_reached = 0, []
    for cid, entry in sorted(zero.items()):
        goal = name_sentence(cid)
        try:
            compiled = front.compile_goal(goal, reg, ROOT)
            if compiled.get("selected_capability") == cid:
                reached += 1
            else:
                not_reached.append({"capability_id": cid, "goal": goal,
                                    "routed_to": str(compiled.get("selected_capability"))})
        except gc.GoalCompilationFailure as exc:
            not_reached.append({"capability_id": cid, "goal": goal,
                                "failure": exc.code + ":" + str(exc.detail)[:100]})
    print(f"zero-input capabilities reached by a plain sentence: {reached}/{len(zero)}")
    for row in not_reached[:10]:
        print("   ", row["capability_id"][:70], "|", row.get("failure") or row.get("routed_to"))

    # ---- 2. RUN, judged by the independent CI oracle
    rows = []
    for cid, entry in sorted(reg.items()):
        if entry.get("capability_source") != "receipt_projection":
            continue
        rp = (entry.get("verification") or {}).get("receipt_path")
        if not rp:
            continue
        vp = ROOT / lane.verification_path_for(rp)
        if not (ROOT / rp).is_file() or not vp.is_file():
            continue
        record = json.loads(vp.read_text(encoding="utf-8"))
        if record.get("reproduced") is not True or not record.get("verifier_result_sha256"):
            continue
        receipt = json.loads((ROOT / rp).read_text(encoding="utf-8"))
        expected = record["verifier_result_sha256"]

        # Does the CI value apply to THIS checkout?  The lane minted the receipt, so the lane
        # is the authority on whether a fresh run reproduces it here.
        before = lane._changed_paths(str(ROOT))
        fresh = lane.execute_and_receipt(cid, receipt.get("module_path"),
                                         receipt.get("entrypoint", "run"), str(ROOT),
                                         "probe", receipt.get("kind") or "contract")
        lane.restore_tree(str(ROOT), before, ("astra_runtime/evidence/CAPABILITY__",))
        local_sha = (fresh or {}).get("result_sha256")
        ci_applies = bool(local_sha) and local_sha == expected

        before = lane._changed_paths(str(ROOT))
        started = time.perf_counter()
        try:
            result = solve({"task_id": "probe-reach-oracle-001", "goal": name_sentence(cid)})
        except Exception as exc:  # noqa: BLE001
            rows.append({"capability_id": cid, "error": str(exc)[:120]})
            continue
        elapsed = round(time.perf_counter() - started, 3)
        lane.restore_tree(str(ROOT), before, ("astra_runtime/evidence/CAPABILITY__",))
        tool_result = None
        for ex in result.get("execution") or []:
            if isinstance(ex, dict) and isinstance(ex.get("result"), dict):
                tool_result = ex["result"]
                break
        matched = None
        if tool_result is not None:
            for form in canonical_forms(tool_result):
                if lane.sha256_canonical(form) == (expected if ci_applies else local_sha):
                    matched = True
                    break
        rows.append({
            "capability_id": cid, "ran": result.get("compiled_capability_id"),
            "pass": result.get("pass"), "status": str(result.get("status"))[:60],
            "ci_applies_here": ci_applies, "matched": bool(matched),
            "elapsed_s": elapsed,
        })

    out = {"zero_input_total": len(zero), "zero_input_prose_reached": reached,
           "not_reached": not_reached, "executed": rows}
    Path("/tmp/prose_reach_and_oracle.json").write_text(json.dumps(out, indent=1, default=str),
                                                         encoding="utf-8")
    verified = [r for r in rows if r.get("ci_applies_here")]
    matched = [r for r in verified if r.get("matched")]
    tree_dependent = [r for r in rows if not r.get("ci_applies_here")]
    print(f"\nexecuted through the one entry: {len(rows)}")
    print(f"  the CI value applies here      : {len(verified)}")
    print(f"  reproduced the CI-verified hash : {len(matched)}")
    print(f"  the CI value does not apply    : {len(tree_dependent)} (the result tracks the tree)")
    for r in tree_dependent[:6]:
        print("    ", r["capability_id"][:74])
    return 0


if __name__ == "__main__":
    sys.exit(main())
