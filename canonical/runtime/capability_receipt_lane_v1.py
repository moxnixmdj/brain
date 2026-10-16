#!/usr/bin/env python3
"""Capability execution receipts — one normalized schema, content-addressed, execution-backed.

WHY (first principles, measured on main @ 370005a)
--------------------------------------------------
`load_verified_registry` admits a capability on a mutable string and a boolean:

    bound    : status == "VERIFIED_BOUND_CAPABILITY"  and  incremental_spend_usd == 0
    extended : status == "VERIFIED_BOUND_CAPABILITY"  and  verification.verified is True

Both are writable by any program.  Measured consequence: flipping 500 extended
statuses fabricates 567 "capabilities" while the referee stays green.

The repo *has* a receipt idiom, but it is not capability-level: the 42 receipt
files referenced by the bound registry are ASTRA mission receipts
(`mission_id`, `mission_sha256`, `state_sha256`, `status: COMPLETE`) — they attest
that a mission completed, not that a module at a given content hash executed and
produced a given effect.  Meanwhile the 67 bound entries use ~150 distinct
verification key names (`workflow_run_id`, `public_run_id`, `regression_run_id`,
`focused_workflow_run_id`, `producer_git_blob`, `verifier_git_blob`, ...) for the
single concept "someone else ran it and here is the reference".

So this module supplies the one part that was missing: a *capability-level*
execution receipt with ONE normalized shape, and it proves claims by running them.

WHAT ONE RECEIPT ASSERTS (nothing more)
---------------------------------------
1. this module, at this exact sha256, loaded;
2. its `run(args, root)` returned a dict, recorded by sha256;
3. these status/pass fields were observed;
4. this identity ran it, on this platform, with zero model dependency.

It does NOT assert correctness, usefulness or independence.  `independent_verifier`
is null unless a *different* identity actually re-ran it.

WHAT IT REFUSES TO DO
---------------------
Never flips a `status`.  Never writes a registry.  Never deletes.  A receipt is
evidence; promotion stays in the governed lane.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import platform
import signal
import sys
import time
from typing import Any

SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"
VERIFICATION_SCHEMA = "PROJECT_BRAIN_CAPABILITY_INDEPENDENT_VERIFICATION_V1"
RECEIPT_DIR = "canonical/astra_runtime/evidence"
EXTENDED = "canonical/runtime/AUTONOMOUS_CAPABILITY_EXTENDED_REGISTRY_V1.json"
BOUND = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
PROJECTION = "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json"
ENTRYPOINTS = ("run", "execute")
ARGS_NAMES = ("args", "request", "inputs", "params", "payload")
PROBE_TIMEOUT_S = 10


class _Timeout(Exception):
    pass


def _alarm(_s, _f):
    raise _Timeout("probe timeout")


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_canonical(value: Any) -> str:
    """Hash a result deterministically, independent of dict ordering."""
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=repr)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def contract_shape(path: str | os.PathLike) -> tuple[str, str] | None:
    """(entrypoint, second_param) if the module speaks `fn(args, root) -> dict`."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in ENTRYPOINTS:
            continue
        params = [a.arg for a in node.args.posonlyargs + node.args.args]
        if len(params) == 2 and params[0] in ARGS_NAMES:
            return node.name, params[1]
    return None


def receipt_path_for(capability_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in capability_id)
    return f"{RECEIPT_DIR}/CAPABILITY__{safe}__EXECUTION_RECEIPT.json"


def verification_path_for(receipt_path: str) -> str:
    return receipt_path.replace("__EXECUTION_RECEIPT.json", "__INDEPENDENT_VERIFICATION.json")


def execute_and_receipt(capability_id: str, module_path: str, entrypoint: str,
                        root: str, ran_by: str) -> dict[str, Any] | None:
    """Run one capability and return its receipt. Returns None if it did not run."""
    started = time.perf_counter()
    module_sha = sha256_file(os.path.join(root, module_path))
    module_name = "pb_receipt_lane_" + module_sha[:16]
    outcome = "UNKNOWN"
    result: Any = None
    observed: dict[str, Any] = {}
    try:
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(root, module_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(PROBE_TIMEOUT_S)
        try:
            spec.loader.exec_module(module)
            fn = getattr(module, entrypoint, None)
            if not callable(fn):
                return None
            result = fn({}, root)
        finally:
            signal.alarm(0)
    except BaseException:  # noqa: BLE001 - a failed probe is data, not an error
        return None
    finally:
        # Deliberately NOT popped from sys.modules: these modules are the brain's own runtime
        # and later ones resolve earlier ones through the import system.  Popping here silently
        # broke 90 of 150 executions (measured 29 receipts with the pop, 119 without).
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

    if not isinstance(result, dict):
        return None
    outcome = "EXECUTED"
    for field in ("status", "pass", "output_verified"):
        if field in result:
            observed[field] = result[field]

    return {
        "schema": SCHEMA,
        "capability_id": capability_id,
        "module_path": module_path,
        "module_sha256": module_sha,
        "entrypoint": entrypoint,
        "invoked_args": {},
        "outcome": outcome,
        "observed": observed,
        "result_sha256": sha256_canonical(result),
        "result_key_count": len(result),
        "elapsed_ms": elapsed_ms,
        "executor": "run_adapter_locally_contract",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "ran_by": ran_by,
        "runtime": {"python": platform.python_version(), "platform": platform.system().lower()},
        "independent_verifier": None,
        "independent_run_reference": None,
    }


def verify_producer_receipts(root: str, ran_by: str,
                             run_reference: Mapping[str, Any] | None) -> dict[str, Any]:
    """Re-execute producer receipts as a DIFFERENT identity and stamp only what reproduces.

    Independence is the whole point (AGENTS.md rule 4: "Verification means someone else ran
    it").  A producer receipt is self-issued and admits nothing on its own.  This runs the
    same module again, and writes a verification record ONLY when the observed result hash
    matches the producer's.  Mismatch, crash or timeout writes nothing and is reported.

    `independent_run_reference` must carry a platform-attested run id.  A reference this
    process invented itself is not independence, and the admission gate refuses references
    without `github_run_id` for exactly that reason.
    """
    import glob as _glob

    produced: list[str] = []
    reproduced: list[str] = []
    mismatched: list[str] = []
    unreadable: list[str] = []

    for receipt_path in sorted(_glob.glob(os.path.join(root, RECEIPT_DIR, "CAPABILITY__*__EXECUTION_RECEIPT.json"))):
        rel = os.path.relpath(receipt_path, root)
        try:
            producer = json.loads(open(receipt_path, encoding="utf-8").read())
        except (OSError, ValueError):
            unreadable.append(rel)
            continue
        if producer.get("schema") != SCHEMA or not producer.get("capability_id"):
            unreadable.append(rel)
            continue
        if producer.get("ran_by") == ran_by:
            # Same identity: not an independent run at all. Never count it.
            mismatched.append(rel)
            continue

        fresh = execute_and_receipt(producer["capability_id"], producer["module_path"],
                                   producer["entrypoint"], root, ran_by)
        if fresh is None or fresh.get("result_sha256") != producer.get("result_sha256"):
            mismatched.append(rel)
            continue

        record = {
            "schema": VERIFICATION_SCHEMA,
            "capability_id": producer["capability_id"],
            "module_path": producer["module_path"],
            "module_sha256": producer["module_sha256"],
            "producer_receipt_path": rel,
            "producer_ran_by": producer.get("ran_by"),
            "producer_result_sha256": producer.get("result_sha256"),
            "verifier_result_sha256": fresh.get("result_sha256"),
            "reproduced": True,
            "independent_verifier": ran_by,
            "independent_run_reference": dict(run_reference or {}),
            "elapsed_ms": fresh.get("elapsed_ms"),
            "model_dependency_count": 0,
        }
        out_path = os.path.join(root, verification_path_for(rel))
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
        produced.append(rel)
        reproduced.append(producer["capability_id"])

    return {"producer_receipts": len(produced) + len(mismatched) + len(unreadable),
            "reproduced": len(reproduced), "mismatched": len(mismatched),
            "unreadable": len(unreadable), "capability_ids": reproduced}


def discover(root: str) -> list[tuple[str, str, str]]:
    """Contract-shaped inventory entries not already live in the bound registry."""
    extended = json.load(open(os.path.join(root, EXTENDED), encoding="utf-8"))["capabilities"]
    bound = json.load(open(os.path.join(root, BOUND), encoding="utf-8"))["capabilities"]
    out: list[tuple[str, str, str]] = []
    for cid, entry in extended.items():
        if cid in bound:
            continue
        path = str((entry.get("source") or {}).get("path") or "")
        if not path or not os.path.isfile(os.path.join(root, path)):
            continue
        shape = contract_shape(os.path.join(root, path))
        if shape is None:
            continue
        out.append((cid, path, shape[0]))
    return out


def projection_entry(receipt: dict[str, Any]) -> dict[str, Any]:
    """A registry entry in the shape the loader and `run_adapter_locally` consume.

    Derived from the receipt, never hand-written.  `status` is deliberately left
    as the inventory value: a receipt is evidence, not a promotion.
    """
    cid = receipt["capability_id"]
    stem = os.path.basename(receipt["module_path"])[:-3]
    keywords: list[str] = []
    for token in stem.split("_"):
        if len(token) > 2 and token not in keywords:
            keywords.append(token)
    return {
        "status": "RECEIPT_BACKED_PENDING_PROMOTION",
        "incremental_spend_usd": 0,
        "cost": 1,
        "adapter_module": stem,
        "entrypoint": receipt["entrypoint"],
        "keywords": keywords[:24],
        "platforms": ["linux"],
        "requires": [],
        "provides": [cid],
        "source": {"type": "repository_python_source", "path": receipt["module_path"],
                   "adapter_path": receipt["module_path"]},
        "action_template": {"type": "invoke_capability", "args": {"capability_id": cid},
                            "expect": {"type": "field_nonempty", "field": "status"}},
        "verification": {
            "receipt_path": receipt["receipt_path"],
            "module_sha256": receipt["module_sha256"],
            "observed_effect": receipt["observed"],
            "model_dependency_count": 0,
            "producer_independent": receipt["independent_verifier"] is not None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Issue content-addressed capability execution receipts.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ran-by", default=os.environ.get("BRAIN_RUNNER_IDENTITY", "local-session"))
    ap.add_argument("--verify", action="store_true",
                    help="re-execute producer receipts as this identity and stamp only reproductions")
    ap.add_argument("--run-reference-json", default=os.environ.get("BRAIN_RUN_REFERENCE", ""),
                    help='platform-attested run reference, e.g. \'{"github_run_id": 123}\'')
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)

    # The brain's own modules import each other as `canonical.runtime.*`.  Run as a script,
    # sys.path[0] is this file's directory, so those imports fail immediately -- measured 29
    # receipts without the repository root on sys.path, 119 with it.
    if root not in sys.path:
        sys.path.insert(0, root)

    if args.verify:
        run_reference = {}
        if args.run_reference_json.strip():
            run_reference = json.loads(args.run_reference_json)
        result = verify_producer_receipts(root, args.ran_by, run_reference)
        result["independent_verifier"] = args.ran_by
        result["run_reference"] = run_reference
        result["note"] = ("only reproductions are stamped; a reference without github_run_id "
                          "cannot admit anything")
        print(json.dumps(result, indent=1))
        return 0

    candidates = discover(root)
    if args.limit:
        candidates = candidates[: args.limit]

    os.makedirs(os.path.join(root, RECEIPT_DIR), exist_ok=True)
    receipts: list[dict[str, Any]] = []
    started = time.perf_counter()
    for cid, path, entrypoint in candidates:
        receipt = execute_and_receipt(cid, path, entrypoint, root, args.ran_by)
        if receipt is None:
            continue
        receipt["receipt_path"] = receipt_path_for(cid)
        with open(os.path.join(root, receipt["receipt_path"]), "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=1, sort_keys=True)
        receipts.append(receipt)
    elapsed = time.perf_counter() - started

    entries = {r["capability_id"]: projection_entry(r) for r in receipts}
    with open(os.path.join(root, PROJECTION), "w", encoding="utf-8") as fh:
        json.dump({"schema": "PROJECT_BRAIN_CAPABILITY_RECEIPT_PROJECTION_V1",
                   "count": len(entries), "entries": entries}, fh, indent=1, sort_keys=True)

    print(json.dumps({
        "candidates": len(candidates),
        "receipts_issued": len(receipts),
        "wall_time_s": round(elapsed, 3),
        "throughput_per_s": round(len(candidates) / elapsed, 1) if elapsed else None,
        "receipt_dir": RECEIPT_DIR,
        "projection": PROJECTION,
        "status_flipped": False,
        "independent_verifier": None,
        "note": "evidence only; promotion requires a different identity to re-run",
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
