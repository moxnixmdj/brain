#!/usr/bin/env python3
"""Does each capability's declared verification actually observe anything?

A MUTATION SCORE FOR THE REGISTRY, MEASURED NOT ASSERTED.

Twenty-nine of the seventy-four capabilities declared

    "expect": {"field": "output_verified", "type": "field_equals", "value": true}

and their adapters assign that literal at the end of run(). The field
observes nothing. It is the proposer grading its own homework, and it
survives every perturbation of the artifact -- which is the definition of
decoration. Mutation testing says the same thing from the other side: a
mutant no assertion can kill is not a test.

The repair was compositional. `_independent_artifact_check` re-reads the
artifact from disk, which the adapter cannot influence, so the claim and
the bytes are compared by someone other than the claimant. That covers
every capability that names an `output_path`; the rest stay uncovered and
are named here rather than assumed to be fine.

TWO THINGS MUST NOT BE CONFLATED, AND THIS TOOL MEASURES ONLY THE FIRST.

  (A) The declared `expect` is a constant, so the declared check cannot
      fail. This is what is counted below.
  (B) The capability can still fail -- most do, by raising. But an
      exception is the PROPOSER reporting on itself. An independent check
      is someone else saying the bytes are wrong. The whole point of
      "verification independent of the proposer" is the second, so (A)
      matters even where (B) holds.

A verifier-style capability -- `xlsx.table.verify_against_json_records`
re-opens the workbook with a reader the producer did not use, and compares
it against canonical records -- is genuinely independent in substance
while its declared `expect` is still a constant. It is listed as uncovered
because the declared check cannot express what the adapter actually does,
not because the work is unchecked.

This tool exists because the finding was a number someone might quote once
and then stop checking. Run it to get the current score.

    python3 canonical/runtime/expect_discrimination_v1.py

Exit status is 0 when every capability's verification can fail, 1 when any
is dead and uncovered.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_EXPECT_DISCRIMINATION_V1"
ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "canonical" / "runtime" / "bound_capabilities"


def _load_registry() -> dict:
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import h100_computer_use_registry_v1 as CU
    reg = dict(GA.load_registry())
    reg.update(CU.bound_entries())
    return reg


def _declared_constants(adapter: str) -> dict[str, bool]:
    """Fields an adapter always sets to one literal, so they cannot vary."""
    path = ADAPTERS / (str(adapter or "") + ".py")
    if not path.is_file():
        return {}
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except Exception:
        return {}
    always: dict[str, bool] = {}
    seen: dict[str, set] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, val in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    seen.setdefault(key.value, set()).add(
                        val.value if isinstance(val, ast.Constant) else None)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and isinstance(target.slice.value, str)):
                    seen.setdefault(target.slice.value, set()).add(
                        node.value.value if isinstance(node.value, ast.Constant)
                        else None)
    for field, values in seen.items():
        if len(values) == 1:
            only = next(iter(values))
            if only is True or only is False:
                always[field] = only
    return always


def _has_output_claim(adapter: str) -> bool:
    """Can `_independent_artifact_check` observe this adapter's output?

    Two ways a dead `expect` becomes checkable, and both are real:

    * the adapter names its artifact with `output_path` + a sha256, so the bytes behind the claim
      can be re-read; or
    * a re-inspector is registered for the capability in
      `raw_goal_trace_acceptance_v1.INSPECTORS`, which re-opens the artifact itself and can refuse.

    The second is not a widening. A registered inspector returns a boolean the acceptance path
    obeys, so a constant `pass` in the result is no longer the only evidence. Capabilities with
    neither remain DEAD_UNCOVERED.
    """
    path = ADAPTERS / (str(adapter or "") + ".py")
    if path.is_file():
        text = path.read_text(errors="replace")
        if ("output_path" in text) and ("sha256" in text):
            return True
    return False


def _has_registered_inspector(capability_id: str) -> bool:
    """Is there a re-inspector that re-opens this capability's artifact?

    Imported lazily and defensively: this measurement must still run when the acceptance module
    cannot be imported, in which case nothing is counted as covered.
    """
    try:
        from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
    except Exception:
        return False
    return capability_id in getattr(acceptance, "INSPECTORS", {})


def measure() -> dict:
    reg = _load_registry()
    rows = []
    for cid, entry in sorted(reg.items()):
        expect = (entry.get("action_template") or {}).get("expect") or {}
        field = str(expect.get("field") or "").strip()
        adapter = str(entry.get("adapter_module") or "")
        constants = _declared_constants(adapter)
        dead = field in constants
        covered = _has_output_claim(adapter) or _has_registered_inspector(cid)
        rows.append({
            "capability_id": cid,
            "expect_field": field or None,
            "constant": constants.get(field) if dead else None,
            "dead": dead,
            "covered_by_reread": covered,
            "status": ("COVERED" if covered else "DEAD_UNCOVERED") if dead
                      else "DISCRIMINATIVE",
        })
    total = len(rows)
    dead = [r for r in rows if r["dead"]]
    uncovered = [r for r in rows if r["status"] == "DEAD_UNCOVERED"]
    return {
        "schema": SCHEMA,
        "capabilities": total,
        "dead_expects": len(dead),
        "dead_and_uncovered": len(uncovered),
        "discrimination_pct": round(100.0 * (total - len(uncovered)) / total, 1)
        if total else 0.0,
        "rows": rows,
    }


def main() -> int:
    m = measure()
    print("%s\n" % m["schema"])
    print("capabilities            : %d" % m["capabilities"])
    print("constant (dead) expects : %d" % m["dead_expects"])
    print("dead and uncovered      : %d" % m["dead_and_uncovered"])
    print("discrimination          : %.1f%%" % m["discrimination_pct"])
    print()
    for r in m["rows"]:
        if r["status"] == "DISCRIMINATIVE":
            continue
        print("  %-16s %-52s %s" % (
            r["status"], r["capability_id"][:52], r["expect_field"]))
    return 1 if m["dead_and_uncovered"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
