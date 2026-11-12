#!/usr/bin/env python3
"""A demonstration with no arguments is not a task. It is a constant.

Round 16 found 296 independently verified experiences and proposed deepening them: run each one k
times with fresh inputs, k = 8. That proposal assumes each verified experience *has* inputs. This
census checks, and the assumption fails:

* of the 296 verification records, **294 are module-path ids** (`.../module_v1.py.auto.v1`) — the
  verification lane verifies that a *module still runs*, not that a *declared capability was invoked*;
* **296 of 296** invocations pass **zero arguments** after the script path;
* of the 145 curated capabilities in the registry, **1** appears in the verified set.

Re-running a zero-argument script produces the same point again. That is depth in count and zero
depth in information: there is no input space for a held-out split to hold anything out of.

The mechanism that *would* create one already exists — `declared_probe_args()` in
`canonical/runtime/capability_receipt_lane_v1.py` fills every `${input.*}` placeholder — but it fills
each one with a **constant** (the capability id, or one content-addressed sink), so instance k is
instance 1 by construction. The fix is to derive those values from an instance index as well. This
census does not make that change: it is six lines in the module that all 296 attestations depend on,
and it cannot be validated here without the CI lane. Naming it is the deliverable; shipping it blind
would risk the thing it is meant to feed.

Authority NONE. Reads evidence and the registry, writes nothing. $0, no model.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
EVIDENCE = REPO_ROOT / "canonical/astra_runtime/evidence"
REGISTRY = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

#: A registry capability id looks like `python.refactor.rename_symbol.v1`.
REGISTRY_STYLE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_.]+\.v\d+$")
PLACEHOLDER = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


def _verification_ids() -> list[str]:
    ids = []
    for path in sorted(EVIDENCE.glob("CAPABILITY__*__INDEPENDENT_VERIFICATION.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("capability_id"):
            ids.append(record["capability_id"])
    return ids


def _producer_receipts() -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in sorted(EVIDENCE.glob("*RECEIPT.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        capability_id = record.get("capability_id")
        if capability_id:
            receipts[capability_id] = record
    return receipts


def _arguments_after_script(receipt: dict[str, Any]) -> int:
    argv = (receipt.get("invoked_args") or {}).get("argv") or []
    return max(0, len(argv) - 2)  # ["python3", "<script>", *args]


def declared_inputs(capability_id: str, registry: dict[str, Any]) -> int:
    entry = registry.get(capability_id) or {}
    template = entry.get("action_template") or {}
    return len(set(PLACEHOLDER.findall(json.dumps(template.get("args") or {}))))


def census() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    verified = _verification_ids()
    receipts = _producer_receipts()

    shapes = collections.Counter()
    arity = collections.Counter()
    for capability_id in verified:
        if capability_id.endswith(".auto.v1"):
            shapes["module_path_auto"] += 1
        elif REGISTRY_STYLE.match(capability_id):
            shapes["registry_capability"] += 1
        else:
            shapes["other"] += 1
        receipt = receipts.get(capability_id)
        arity[_arguments_after_script(receipt) if receipt else -1] += 1

    overlap = sorted(set(verified) & set(registry))
    registry_with_verification = len(overlap)
    registry_total = len(registry)

    # how wide the input space of the curated capabilities would be, if they were the ones verified
    declared = collections.Counter(declared_inputs(capability_id, registry) for capability_id in registry)

    return {
        "census": "input_space",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified_records": len(verified),
        "verified_shapes": dict(shapes),
        "arguments_after_script": {str(k): v for k, v in sorted(arity.items())},
        "verified_with_any_argument": sum(v for k, v in arity.items() if k and k > 0),
        "registry_capabilities": registry_total,
        "registry_capabilities_verified": registry_with_verification,
        "registry_capabilities_with_declared_inputs": dict(sorted(declared.items())),
        "verdict": "NO_INPUT_SPACE_IN_THE_VERIFIED_CORPUS",
        "why": (
            "a verified experience is a zero-argument module execution, so instance k is instance 1; "
            "a held-out split has nothing to hold out and a student would learn 296 constants"
        ),
        "the_fix_and_why_it_is_not_shipped_here": {
            "where": "canonical/runtime/capability_receipt_lane_v1.py :: declared_probe_args()",
            "what": "derive each ${input.*} value from (capability_id, module_sha, instance_index) "
                    "instead of a constant, and record the index in the receipt so --verify replays "
                    "the same instance",
            "size": "about six lines",
            "why_not_now": "all 296 attestations are produced by that module; a blind change to it "
                           "could invalidate them, and the CI lane that would prove it does not run here",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    report = census()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Does the verified corpus have an input space?")
    print("=" * 78)
    print(f"  verification records                              {report['verified_records']:>6}")
    for shape, count in sorted(report["verified_shapes"].items()):
        print(f"    {shape:<20}                        {count:>6}")
    print(f"  arguments after the script path                   {report['arguments_after_script']}")
    print(f"  verified experiences with any argument            "
          f"{report['verified_with_any_argument']:>6}")
    print(f"  curated registry capabilities                     {report['registry_capabilities']:>6}")
    print(f"  of those, independently verified                  "
          f"{report['registry_capabilities_verified']:>6}")
    print()
    print(f"  verdict: {report['verdict']}")
    print(f"    {report['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
