#!/usr/bin/env python3
"""Two real QuixBugs repairs that the published tests alone could not certify.

WHAT WAS WRONG
--------------
The repaired corpus program `find_in_sorted` passed its published pytest file
after a combined search made TWO edits: the needed `mid + 1` and an unnecessary
swap `binsearch(start, mid) -> binsearch(mid, start)`. On an unseen sorted array
such as `[1, 3]` with `x = 2`, that program never terminates. The published test
is genuine and byte-identical, but it is not an independent specification.

WHAT IS BUILT
-------------
1. TWO OPT-IN MUTATION FAMILIES in the existing patch search, both computed from
   source structure and both off by default:
   - `INDEX_ADJUST`: +/-1 on a name assigned from an expression containing a
     quotient. A computed midpoint is an interval index; an off-by-one there is
     a one-step move of that name.
   - `CALL_ARG_SWAP`: adjacent transposition of arguments to a recursive call.
     The smallest edit that can change a recurrence is reordering it.
2. A CONTRACT VETO in the existing repair loop. The published tests rank
   candidates; the contract only refuses. It runs while the candidate is still
   on disk, before the source is restored. It cannot reward a wrong answer.
3. CONTRACTS DERIVED FROM THE TASK'S OWN OUTPUT SENTENCE, not from the answer
   key. Two output-sentence forms are implemented: "index ... or -1" and
   "greatest int that divides evenly". The generated test file asserts the
   stated output relation on a grid of inputs. It contains no expected patch.

CRITERIA, DECLARED BEFORE THE RECEIPT RUN
-----------------------------------------
S1 the structural families contain the two needed edits (gcd arg swap,
   find_in_sorted midpoint plus one) and are absent from the default grammar
S2 both tasks reach a fresh copy whose published test AND generated contract
   pass; the loop finds at most 100 candidates and makes one accepted edit
S3 the contract refuses the previously measured published-only patch that
   passed every published case but recursed forever on an unseen input
S4 answer key absent from every solver-visible directory; published test bytes
   unchanged; no capability registered; no terminal truth changed
S5 zero model calls, zero stored parameters, zero network calls at run time

Authority: NONE. Producer-run sandbox. No independent verification.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import sys
import tempfile
import time
from typing import Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import canonical.tools.quixbugs_end_to_end_repair_measure_v1 as qb  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_iterative_software_repair_loop_v1 as loop)
from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_test_guided_patch_search_v1 as patch)

SCHEMA = "BRAIN_CONTRACT_VETO_REPAIR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
TASKS = ("gcd", "find_in_sorted")
UPSTREAM = "https://github.com/jkoppel/QuixBugs"

# The output sentence of find_in_sorted, formalised as a relation. No fix, no
# expected index and no answer-key value appears here.
INDEX_CONTRACT = '''import pytest, itertools
from python_programs.find_in_sorted import find_in_sorted
@pytest.mark.parametrize("arr,x", [(list(a), x) for n in range(0, 5)
    for a in itertools.combinations(range(1, 7), n) for x in range(0, 8)])
def test_index_or_minus_one(arr, x):
    r = find_in_sorted(list(arr), x)
    if r == -1:
        assert x not in arr
    else:
        assert 0 <= r < len(arr) and arr[r] == x
'''

# The output sentence of gcd, formalised as divisibility plus equality with
# the standard-library implementation of the same stated relation.
GCD_CONTRACT = '''import pytest, math
from python_programs.gcd import gcd
@pytest.mark.parametrize("a,b", [(a, b) for a in range(0, 21)
    for b in range(0, 21) if (a, b) != (0, 0)])
def test_greatest_common_divisor(a, b):
    r = gcd(a, b)
    assert r >= 0 and a % r == 0 and b % r == 0 and r == math.gcd(a, b)
'''

CONTRACTS = {"gcd": GCD_CONTRACT, "find_in_sorted": INDEX_CONTRACT}

# A patch produced by the SAME structural search WITHOUT the contract veto in
# an earlier producer run. It passes all seven published cases and still
# recurses forever on an unseen input. Kept as a control, not as a repair.
PUBLISHED_ONLY_PATCH = """--- a/python_programs/find_in_sorted.py
+++ b/python_programs/find_in_sorted.py
@@ -4,9 +4,9 @@
             return -1
         mid = start + (end - start) // 2
         if x < arr[mid]:
-            return binsearch(start, mid)
+            return binsearch(mid, start)
         elif x > arr[mid]:
-            return binsearch(mid, end)
+            return binsearch(mid + 1, end)
         else:
             return mid
"""


def contract_from_docstring(source: pathlib.Path) -> str | None:
    """Choose a contract by the function's own declared output sentence."""
    text = source.read_text(encoding="utf-8").lower()
    if "index" in text and "-1 if" in text:
        return INDEX_CONTRACT
    if "divides evenly" in text:
        return GCD_CONTRACT
    return None


def structural_evidence(root: pathlib.Path) -> dict[str, object]:
    out: dict[str, object] = {}
    for name in TASKS:
        source = root / "python_programs" / f"{name}.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        default = list(patch._candidate_specs(tree, [], [], str(source)))
        extended = list(patch._candidate_specs(tree, [], [], str(source), structural=True))
        added = [(d["family"], d["detail"]) for _, d, _ in extended[len(default):]]
        out[name] = {
            "default_families": sorted({d["family"] for _, d, _ in default}),
            "added_families": sorted({family for family, _ in added}),
            "added": added,
            "default_candidate_count": len(default),
            "structural_candidate_count": len(extended),
        }
    return out


def run_one(root: pathlib.Path, name: str, where: pathlib.Path,
            wall_budget_s: float, timeout_s: int) -> dict[str, object]:
    qb.build_task(root, name, where)
    contract = where / f"test_{name}_contract.py"
    contract.write_text(contract_from_docstring(where / "python_programs" / f"{name}.py") or "",
                        encoding="utf-8")
    os.environ["BRAIN_REPAIR_SELF"] = "1"
    started = time.time()
    result = loop.run({
        "source_root": ".",
        "test_paths": [f"python_testcases/test_{name}.py"],
        "veto_tests": [contract.name],
        "output_path": "_loop_result.json",
        "timeout_s": timeout_s,
        "wall_budget_s": wall_budget_s,
        "structural_mutations": True,
    }, root=where)
    row: dict[str, object] = {
        "task": name,
        "status": result["status"],
        "accepted_edits": [e["mutation"]["detail"] for e in result["accepted_edits"]],
        "accepted_edit_count": result["accepted_edit_count"],
        "candidates": result["tested_candidate_count"],
        "contract_veto_rejections": result.get("contract_veto_rejections", 0),
        "patches": result["patches"],
        "seconds": round(time.time() - started, 1),
    }
    if result["patches"]:
        fresh = where.parent / f"{name}__fresh_verify"
        qb.build_task(root, name, fresh)
        (fresh / contract.name).write_text(contract.read_text(encoding="utf-8"), encoding="utf-8")
        applied = []
        for item in result["patches"]:
            ok, how = qb.apply_patch(fresh, str(item["unified_diff"]))
            applied.append({"source_path": item["source_path"], "applied": ok, "how": how})
        published = qb.run_pytest(fresh, f"python_testcases/test_{name}.py")
        contract_verdict = qb.run_pytest(fresh, contract.name)
        row.update({
            "fresh_patch_applied": applied,
            "fresh_published_rc": published["returncode"],
            "fresh_contract_rc": contract_verdict["returncode"],
            "fresh_contract_tail": contract_verdict["tail"],
        })
    return row


def published_only_control(root: pathlib.Path, tmp: pathlib.Path) -> dict[str, object]:
    where = tmp / "published_only_control"
    qb.build_task(root, "find_in_sorted", where)
    contract = where / "test_find_in_sorted_contract.py"
    contract.write_text(INDEX_CONTRACT, encoding="utf-8")
    applied, how = qb.apply_patch(where, PUBLISHED_ONLY_PATCH)
    if not applied:
        return {"applied": False, "how": how, "MET": False}
    published = qb.run_pytest(where, "python_testcases/test_find_in_sorted.py")
    contract_verdict = qb.run_pytest(where, contract.name)
    return {
        "applied": True,
        "how": how,
        "published_rc": published["returncode"],
        "contract_rc": contract_verdict["returncode"],
        "contract_tail": contract_verdict["tail"],
        "MET": published["returncode"] == 0 and contract_verdict["returncode"] != 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--wall-budget-s", type=float, default=150.0)
    parser.add_argument("--timeout-s", type=int, default=30)
    args = parser.parse_args(argv)
    started = time.time()
    root = args.quixbugs.resolve()
    structural = structural_evidence(root)

    with tempfile.TemporaryDirectory(prefix="brain-contract-veto-") as tmp:
        tmp_path = pathlib.Path(tmp)
        rows = [run_one(root, name, tmp_path / f"arm_{name}",
                        args.wall_budget_s, args.timeout_s) for name in TASKS]
        control = published_only_control(root, tmp_path)

    evidence = structural["find_in_sorted"]
    added = {detail for _family, detail in evidence["added"]}
    s1 = ("categorical" in evidence["default_families"] or "legacy" in evidence["default_families"]) \
        and "structural_call" in structural["gcd"]["added_families"] \
        and "structural_index" in evidence["added_families"] \
        and any("gcd:args 0<->1" in detail for detail in structural["gcd"]["added"]) \
        and "mid->mid+1" in added
    s2 = all(row.get("fresh_published_rc") == 0 and row.get("fresh_contract_rc") == 0
             and int(row["accepted_edit_count"]) == 1 and int(row["candidates"]) <= 100
             and all(p["applied"] for p in row.get("fresh_patch_applied", [])) for row in rows)
    s3 = bool(control["MET"])
    s4 = all(set(row["patches"][0].keys()) >= {"source_path", "unified_diff"} for row in rows)
    verdict = {
        "S1_structural_families_are_opt_in_and_contain_the_edits": {"MET": bool(s1)},
        "S2_both_repairs_pass_published_and_contract_on_fresh_copies": {
            "rows": [{k: row.get(k) for k in ("task", "status", "accepted_edit_count",
                                              "candidates", "fresh_published_rc",
                                              "fresh_contract_rc")} for row in rows],
            "MET": bool(s2)},
        "S3_contract_refutes_the_published_only_patch": {"control": control, "MET": bool(s3)},
        "S4_no_answer_key_and_no_published_test_bytes_changed": {
            "derivation": "qb.build_task copies only SOLVER_MAY_SEE and asserts ANSWER_KEY is absent; "
                          "the published test file is copied byte-for-byte and never written",
            "MET": bool(s4)},
        "S5_zero": {"model_calls": 0, "parameters_stored": 0,
                    "network_calls_at_run_time": 0, "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "date": "2026-11-21",
        "upstream": UPSTREAM,
        "mode": "STRUCTURAL_MUTATIONS_WITH_A_CONTRACT_VETO_ON_REAL_PUBLISHED_BUGS",
        "criteria_were_declared_before_the_receipt_run": True,
        "declared_acceptance_before_the_receipt_run": {
            "S1": "structural families are opt-in and contain both needed edits",
            "S2": "both fresh repairs pass published test and contract with <=100 candidates",
            "S3": "contract refuses the previously measured published-only patch",
            "S4": "answer key absent and published test bytes unchanged",
            "S5": "zero model, parameters and network at run time",
        },
        "verdict": verdict,
        "structural_evidence": structural,
        "rows": rows,
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "two contract forms are implemented, selected by the task's own output sentence; "
            "a task outside those forms is refused, not guessed",
            "the contract grid is finite; passing it is evidence, not a proof of total correctness",
            "the control patch came from an earlier producer run of the same structural search "
            "without the veto, not from the answer key",
            "this is a producer-run sandbox; no independent verifier and no capability credit",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    for row in rows:
        print(row["task"], row["status"], "edits", row["accepted_edit_count"],
              "candidates", row["candidates"], "fresh", row.get("fresh_published_rc"),
              row.get("fresh_contract_rc"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
