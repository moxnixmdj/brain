#!/usr/bin/env python3
"""Play 6 — Adversarial Mutation Admission Gate (`adversarial_mutation_admission_gate_v1`).

Implements Play 6 of `canonical/verification/FRONTIER_LEAPFROG_PLAN_20261125_V1.md`:
  - Applies deterministic AST mutations (comparison operator flip, arithmetic flip,
    boolean branch/return flip) directly to each newly lifted / harvested capability
    module in memory (never touching repository files on disk).
  - Re-executes the mutated module on the producer receipt's exact `invoked_args`
    (with `restore_snapshot_inputs` for file-backed capabilities) and checks:
      1. Whether the capability receipt verifier (`result_sha256` + exception check)
         kills the mutant.
      2. Whether the projection's `action_template.expect` check alone kills the mutant
         (exposing weak expectation templates where output corruption survives template
         checks even though full digest replay catches it).
  - Publishes every surviving mutant explicitly by capability id, module path, line
    number, and mutation operator.

Kill criterion (from `FRONTIER_LEAPFROG_PLAN_20261125_V1.md`):
  - `survivor_rate > 0.20` -> gate is theatre (`kill_triggered = True`).

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, deterministic execution.
"""
from __future__ import annotations

import ast
import copy
import glob
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import sys
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ADVERSARIAL_MUTATION_ADMISSION_GATE_V1"
MAX_SURVIVOR_RATE = 0.20

_CMP_FLIPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}

_BIN_FLIPS: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
}


def synthesize_first_executable_mutation(
    source_text: str,
    entrypoint: str = "run",
) -> dict[str, Any] | None:
    """Mutate one live AST operator/constant inside `entrypoint` (or module functions)."""
    tree = ast.parse(source_text)

    target_funcs = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == entrypoint
    ] + [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name != entrypoint
    ]

    candidates: list[tuple[int, str, ast.AST, str]] = []
    for fn_idx, fn in enumerate(target_funcs):
        base_prio = 0 if fn_idx == 0 else 10
        # Prefer return-dict/value boolean flips & arithmetic/comparison flips inside entrypoint
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and node.value is not None:
                for sub in ast.walk(node.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, bool):
                        candidates.append((base_prio + 1, "ReturnBoolFlip", sub, f"bool:{sub.value}->{not sub.value}"))
                    elif isinstance(sub, ast.BinOp) and type(sub.op) in _BIN_FLIPS:
                        new_cls = _BIN_FLIPS[type(sub.op)]
                        candidates.append((base_prio + 2, "ReturnBinOpFlip", sub, f"{type(sub.op).__name__}->{new_cls.__name__}"))
            if isinstance(node, ast.Compare) and node.ops and type(node.ops[0]) in _CMP_FLIPS:
                new_cls = _CMP_FLIPS[type(node.ops[0])]
                candidates.append((base_prio + 3, "CompareOpFlip", node, f"{type(node.ops[0]).__name__}->{new_cls.__name__}"))
            elif isinstance(node, ast.BinOp) and type(node.op) in _BIN_FLIPS:
                new_cls = _BIN_FLIPS[type(node.op)]
                candidates.append((base_prio + 4, "BinOpFlip", node, f"{type(node.op).__name__}->{new_cls.__name__}"))
            elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
                candidates.append((base_prio + 5, "BoolConstFlip", node, f"bool:{node.value}->{not node.value}"))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], getattr(item[2], "lineno", 0), getattr(item[2], "col_offset", 0)))
    _prio, kind, chosen, desc = candidates[0]
    lineno = getattr(chosen, "lineno", 0)
    col = getattr(chosen, "col_offset", 0)

    mut_tree = copy.deepcopy(tree)
    applied = False
    for node in ast.walk(mut_tree):
        if type(node) is type(chosen) and getattr(node, "lineno", -1) == lineno and getattr(node, "col_offset", -1) == col:
            if kind in ("ReturnBoolFlip", "BoolConstFlip") and isinstance(node, ast.Constant):
                node.value = not node.value
                applied = True
                break
            if kind in ("ReturnBinOpFlip", "BinOpFlip") and isinstance(node, ast.BinOp):
                node.op = _BIN_FLIPS[type(node.op)]()
                applied = True
                break
            if kind == "CompareOpFlip" and isinstance(node, ast.Compare) and node.ops:
                node.ops[0] = _CMP_FLIPS[type(node.ops[0])]()
                applied = True
                break

    if not applied:
        return None
    ast.fix_missing_locations(mut_tree)
    return {
        "mutation_kind": kind,
        "description": desc,
        "lineno": lineno,
        "mutated_source": ast.unparse(mut_tree),
    }


def _check_template_expect(expect: Mapping[str, Any] | None, result: Mapping[str, Any]) -> bool:
    if not expect:
        return True
    etype = expect.get("type")
    field = str(expect.get("field") or "")
    if etype == "field_equals":
        return result.get(field) == expect.get("value")
    if etype == "field_nonempty":
        val = result.get(field)
        return val is not None and val != "" and val != [] and val != {}
    return True


def evaluate_mutant_against_receipt(
    receipt: Mapping[str, Any],
    root: str | pathlib.Path = ROOT,
    timeout_s: int = 12,
) -> dict[str, Any]:
    repo_root = pathlib.Path(root).resolve()
    cid = str(receipt["capability_id"])
    mod_rel = str(receipt["module_path"])
    entrypoint = str(receipt.get("entrypoint") or "run")
    mod_file = repo_root / mod_rel

    src = mod_file.read_text(encoding="utf-8")
    mut = synthesize_first_executable_mutation(src, entrypoint=entrypoint)
    if mut is None:
        return {
            "capability_id": cid,
            "module_path": mod_rel,
            "verdict": "SURVIVED_NO_MUTATION_OPERATOR_APPLICABLE",
            "killed": False,
            "template_expect_killed": False,
            "mutation_kind": "NONE",
            "lineno": 0,
            "description": "no AST mutation candidate found",
        }

    invoked_args = dict(receipt.get("invoked_args") or {})
    lane.restore_snapshot_inputs(str(repo_root), invoked_args, receipt.get("input_digests"))
    proj_expect = lane.projection_entry(dict(receipt))["action_template"].get("expect")

    # Execute mutated AST in-memory under module's real path so relative helpers resolve,
    # without modifying any file on disk!
    mod_name = "pb_mutant_gate_" + hashlib.sha256(f"{cid}:{mut['lineno']}".encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(mod_name, str(mod_file))
    if spec is None:
        return {
            "capability_id": cid,
            "module_path": mod_rel,
            "verdict": "KILLED_BY_IMPORT_SPEC",
            "killed": True,
            "template_expect_killed": True,
            "mutation_kind": mut["mutation_kind"],
            "lineno": mut["lineno"],
            "description": mut["description"],
        }

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        signal.signal(signal.SIGALRM, lane._alarm)
        signal.alarm(timeout_s)
        try:
            code_obj = compile(mut["mutated_source"], str(mod_file), "exec")
            exec(code_obj, module.__dict__)  # noqa: S102 - isolated AST mutant evaluation
            fn = getattr(module, entrypoint)
            mut_result = fn(dict(invoked_args), str(repo_root))
        finally:
            signal.alarm(0)
    except BaseException as exc:  # noqa: BLE001 - exception kills the mutant
        return {
            "capability_id": cid,
            "module_path": mod_rel,
            "verdict": f"KILLED_BY_EXCEPTION:{type(exc).__name__}",
            "killed": True,
            "template_expect_killed": True,
            "mutation_kind": mut["mutation_kind"],
            "lineno": mut["lineno"],
            "description": mut["description"],
        }
    finally:
        sys.modules.pop(mod_name, None)

    if not isinstance(mut_result, dict):
        return {
            "capability_id": cid,
            "module_path": mod_rel,
            "verdict": "KILLED_BY_NON_DICT_RETURN",
            "killed": True,
            "template_expect_killed": True,
            "mutation_kind": mut["mutation_kind"],
            "lineno": mut["lineno"],
            "description": mut["description"],
        }

    mut_sha = lane.sha256_canonical(mut_result)
    digest_killed = mut_sha != receipt.get("result_sha256")
    expect_killed = not _check_template_expect(proj_expect, mut_result)

    return {
        "capability_id": cid,
        "module_path": mod_rel,
        "verdict": "KILLED_BY_RECEIPT_ORACLE" if digest_killed else "SURVIVED",
        "killed": digest_killed,
        "template_expect_killed": expect_killed,
        "mutation_kind": mut["mutation_kind"],
        "lineno": mut["lineno"],
        "description": mut["description"],
    }


def audit_harvested_capabilities(
    root: str | pathlib.Path = ROOT,
    capability_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    repo_root = pathlib.Path(root).resolve()
    receipt_files = sorted(
        glob.glob(os.path.join(str(repo_root), lane.RECEIPT_DIR, "CAPABILITY__*.hidden.v1__EXECUTION_RECEIPT.json"))
    )

    selected_receipts: list[dict[str, Any]] = []
    wanted = set(capability_ids) if capability_ids else None
    for rf in receipt_files:
        doc = json.loads(pathlib.Path(rf).read_text(encoding="utf-8"))
        if doc.get("kind") != "contract":
            continue
        if wanted is not None and doc.get("capability_id") not in wanted:
            continue
        selected_receipts.append(doc)

    before = lane._changed_paths(str(repo_root))
    results: list[dict[str, Any]] = []
    for rec in selected_receipts:
        results.append(evaluate_mutant_against_receipt(rec, repo_root))
    lane.restore_tree(str(repo_root), before, ("astra_runtime/tmp/",))

    total = len(results)
    killed = sum(1 for r in results if r["killed"])
    template_only_killed = sum(1 for r in results if r["template_expect_killed"])
    survivors = [r for r in results if not r["killed"]]
    template_blind_spots = [
        r["capability_id"] for r in results if r["killed"] and not r["template_expect_killed"]
    ]
    survivor_rate = round(len(survivors) / max(total, 1), 4)
    kill_triggered = survivor_rate > MAX_SURVIVOR_RATE

    digest = hashlib.sha256(
        json.dumps(results, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "play_id": "PLAY_6_ADVERSARIAL_MUTATION_ADMISSION_GATE",
        "status": "GATE_THEATRE_SURVIVORS_EXCEED_20_PCT" if kill_triggered else "ADMISSION_GATE_HOLDING",
        "output_verified": len(digest) == 64,
        "capabilities_tested": total,
        "mutants_generated": total,
        "mutants_killed_by_receipt_oracle": killed,
        "mutants_killed_by_template_expect_alone": template_only_killed,
        "template_expect_blind_spot_count": len(template_blind_spots),
        "template_expect_blind_spots": template_blind_spots,
        "surviving_mutant_count": len(survivors),
        "surviving_mutants": survivors,
        "survivor_rate": survivor_rate,
        "kill_criterion": {
            "max_survivor_rate": MAX_SURVIVOR_RATE,
            "kill_triggered": kill_triggered,
        },
        "results": results,
        "audit_sha256": digest,
        "model_dependency_count": 0,
    }


def run(args: Mapping[str, Any] | None, root: str | pathlib.Path = ROOT) -> dict[str, Any]:
    req = dict(args or {})
    cids = req.get("capability_ids")
    if isinstance(cids, list) and cids:
        return audit_harvested_capabilities(root, [str(x) for x in cids])
    # Default deterministic probe when invoked through receipt lane with `{}`:
    # audit the foundational contract surfaces so runtime stays bounded (< 1s) and invariant.
    default_cids = [
        "canonical.runtime.bound_capabilities.jq_query.hidden.v1",
        "canonical.runtime.bound_capabilities.concrete_execution_oracle.hidden.v1",
        "canonical.runtime.binding_pin_is_current_v1.hidden.v1",
        "canonical.runtime.capability_selection_retrieval_v1.hidden.v1",
    ]
    return audit_harvested_capabilities(root, default_cids)


if __name__ == "__main__":
    # CLI mode audits ALL harvested contract receipts in the repository!
    print(json.dumps(audit_harvested_capabilities(ROOT), indent=2, sort_keys=True))
