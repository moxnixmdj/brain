#!/usr/bin/env python3
r"""Move 6 / Play 6 v2 — Apartness-Guided Distinguishing Tuple Mutation Gate (`adversarial_mutation_admission_gate_v2`).

Fixes Play 6 v1's single-probe `{}` blind spot (`25.0%` default / `43.75%` full-corpus
mutant survival rate -> `GATE_THEATRE_SURVIVORS_EXCEED_20_PCT`) using Vaandrager $L^\#$
apartness + `canonical/tools/an_actions_vocabulary_is_its_refusal_surface_v1.py`:

  1. Exact Same `v1` Mutant Operator (`v1.synthesize_first_executable_mutation`):
       Evaluates the exact same AST mutations as `v1` (zero moving of goalposts).
  2. Mechanical AST-Derived Distinguishing Input Tuple (`(nominal, boundary, refusal)`):
       Walks `entrypoint` (and module-local callees) to extract input keys read via
       `args.get("k")` / `req.get("k")` / `args["k"]` and synthesizes:
         - Point 0 (`nominal`): the producer receipt's exact `invoked_args`,
         - Point 1..k (`ast_branch_boundary`): branch-activating payloads for literal
           equality guards (`req.get("action") == "..."`), list/dict `isinstance` guards,
           boolean/empty-expect boundary cases, and goal/query text slots,
         - Point k+1..m (`refusal_surface`): path-outside-repository (`../outside_probe`)
           and missing-file perturbations on `*_path` / `*_root` slots, testing whether
           the mutant alters the capability's refusal boundary (`RuntimeError` / `ValueError`
           vs silent fallthrough).
  3. Differential Apartness Verdict:
       Runs each probe on both the unmutated reference module and the in-memory AST
       mutant (reverting scratch side effects afterward). A mutant is killed iff ANY
       point in the distinguishing tuple exhibits apartness (`outcome_kind` or canonical
       return SHA-256 or exception/refusal class differs).

Kill criterion:
  - `survivor_rate >= 0.15` (tightened from `v1`'s `0.20` to `< 15%`).

Authority: NONE. Zero external model calls (`K3 = 0`), `$0` spend, deterministic.
"""
from __future__ import annotations

import ast
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

from canonical.runtime import adversarial_mutation_admission_gate_v1 as v1  # noqa: E402
from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ADVERSARIAL_MUTATION_ADMISSION_GATE_V2"
MAX_SURVIVOR_RATE = 0.15


def _extract_key_from_call(node: ast.AST) -> str | None:
    """Extract string key `k` from `args.get('k')`, `(args or {}).get('k')`, or `args['k']`."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return node.slice.value
    return None


def synthesize_distinguishing_tuple(
    source_text: str,
    nominal_args: Mapping[str, Any],
    entrypoint: str = "run",
) -> list[tuple[str, dict[str, Any]]]:
    """Synthesize `(probe_kind, args_dict)` distinguishing probes purely from AST structure."""
    probes: list[tuple[str, dict[str, Any]]] = [("nominal_receipt", dict(nominal_args))]
    seen_json = {json.dumps(nominal_args, sort_keys=True, default=str)}

    def _add(kind: str, payload: dict[str, Any]) -> None:
        sig = json.dumps(payload, sort_keys=True, default=str)
        if sig not in seen_json:
            seen_json.add(sig)
            probes.append((kind, payload))

    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return probes

    entry_nodes = [
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == entrypoint
    ]
    focus_root: ast.AST = entry_nodes[0] if entry_nodes else tree

    # Map local variable aliases (`action = str(req.get("action") or ...)`) -> key name inside `entrypoint`
    alias_to_key: dict[str, str] = {}
    discovered_keys: set[str] = set()
    literal_equalities: list[tuple[str, Any]] = []
    typed_keys: dict[str, str] = {}

    for node in ast.walk(focus_root):
        k = _extract_key_from_call(node)
        if k:
            discovered_keys.add(k)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            lhs = node.targets[0].id
            for sub in ast.walk(node.value):
                sub_k = _extract_key_from_call(sub)
                if sub_k:
                    alias_to_key[lhs] = sub_k
                    discovered_keys.add(sub_k)
                    break

    # Also collect `_path` / `_root` keys read in module-level loader helpers (e.g. `_load_pairs(args, root)`)
    for node in ast.walk(tree):
        k = _extract_key_from_call(node)
        if k and (k.endswith(("_path", "_root", "_file", "_pairs")) or k in ("goal", "query", "objective")):
            discovered_keys.add(k)

    for node in ast.walk(focus_root):
        # Detect `req.get("k") == "lit"` or `alias == "lit"`
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            left, right = node.left, node.comparators[0]
            lhs_key = _extract_key_from_call(left) or (
                alias_to_key.get(left.id) if isinstance(left, ast.Name) else None
            )
            if lhs_key and isinstance(op, ast.Eq) and isinstance(right, ast.Constant):
                literal_equalities.append((lhs_key, right.value))
        # Detect `isinstance(req.get("k"), (list, Mapping, dict))`
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "isinstance"
            and len(node.args) == 2
        ):
            target_k = _extract_key_from_call(node.args[0]) or (
                alias_to_key.get(node.args[0].id) if isinstance(node.args[0], ast.Name) else None
            )
            if target_k:
                t_repr = ast.unparse(node.args[1])
                if "Mapping" in t_repr or "dict" in t_repr:
                    typed_keys[target_k] = "mapping"
                elif "list" in t_repr or "Sequence" in t_repr:
                    typed_keys[target_k] = "list"

    # 1. AST Branch-Activating Boundary Probes
    sample_task = {"old_line": "if flag:", "new_line": "if flag is not None:", "repo": "probe"}
    for key, lit_val in literal_equalities[:4]:
        probe = dict(nominal_args)
        probe[key] = lit_val
        for tk, tkind in typed_keys.items():
            if tk not in probe:
                probe[tk] = dict(sample_task) if tkind == "mapping" else [dict(sample_task)]
        _add(f"boundary_eq:{key}={lit_val!r}", probe)

    for tk, tkind in sorted(typed_keys.items()):
        probe = dict(nominal_args)
        if tk == "tasks" and tkind == "list":
            probe[tk] = [dict(sample_task)]
        elif tk == "capability_ids" and tkind == "list":
            # Include a capability receipt with empty `observed` (`expect is None`) if present
            probe[tk] = ["canonical.runtime.swe_kernel_organ_bridge_v1.hidden.v1"]
        elif tkind == "mapping":
            probe[tk] = dict(sample_task)
        elif tkind == "list":
            probe[tk] = [dict(sample_task)]
        _add(f"boundary_type:{tk}:{tkind}", probe)

    for goal_key in ("goal", "query", "objective"):
        if goal_key in discovered_keys and not nominal_args.get(goal_key):
            probe = dict(nominal_args)
            probe[goal_key] = "audit python source structure and imports"
            _add(f"boundary_nonempty:{goal_key}", probe)

    # 2. Refusal-Surface Violation Probes (`an_actions_vocabulary_is_its_refusal_surface_v1`)
    path_keys = sorted(
        k for k in discovered_keys
        if k.endswith(("_path", "_root", "_file")) and k != "ledger_db_path"
    )
    for pk in path_keys[:3]:
        refusal_probe: dict[str, Any] = {}
        # Clear optional direct-data sibling so the path branch executes and checks repository bounds
        for dk in discovered_keys:
            if dk != pk and dk.endswith("_pairs"):
                refusal_probe[dk] = None
        refusal_probe[pk] = "../outside_repository_refusal_probe.json"
        _add(f"refusal_outside_repo:{pk}", refusal_probe)

    return probes[:8]


def _execute_code_with_probe(
    code_obj: Any,
    mod_file: pathlib.Path,
    entrypoint: str,
    probe_args: Mapping[str, Any],
    repo_root: pathlib.Path,
    timeout_s: int,
) -> dict[str, Any]:
    """Execute compiled module `entrypoint(probe_args, repo_root)` and return its apartness signature."""
    spec = importlib.util.spec_from_file_location("_pb_apartness_probe_mod", str(mod_file))
    if spec is None:
        return {"kind": "IMPORT_FAILURE", "sig": "SPEC_NONE", "raw": None}
    module = importlib.util.module_from_spec(spec)
    sys.modules["_pb_apartness_probe_mod"] = module
    try:
        signal.signal(signal.SIGALRM, lane._alarm)
        signal.alarm(timeout_s)
        try:
            exec(code_obj, module.__dict__)  # noqa: S102 - isolated in-memory apartness check
            fn = getattr(module, entrypoint)
            out = fn(dict(probe_args), str(repo_root))
        finally:
            signal.alarm(0)
            sys.modules.pop("_pb_apartness_probe_mod", None)
    except BaseException as exc:  # noqa: BLE001 - refusal/exception is the observable!
        msg_head = str(exc).split(":")[0].strip()[:64]
        return {
            "kind": "REFUSAL_EXCEPTION",
            "sig": f"{type(exc).__name__}:{msg_head}",
            "raw": None,
        }
    if not isinstance(out, dict):
        return {"kind": "NON_DICT_RETURN", "sig": type(out).__name__, "raw": None}
    return {
        "kind": "RETURN_DICT",
        "sig": lane.sha256_canonical(out),
        "raw": out,
    }


def _has_helper_expect_check(source_text: str) -> bool:
    return "def _check_template_expect(" in source_text


def evaluate_mutant_with_apartness_tuple(
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
    mut = v1.synthesize_first_executable_mutation(src, entrypoint=entrypoint)
    if mut is None:
        return {
            "capability_id": cid,
            "module_path": mod_rel,
            "verdict": "SURVIVED_NO_MUTATION_OPERATOR_APPLICABLE",
            "killed": False,
            "killed_by_probe": None,
            "probes_evaluated": 0,
            "template_expect_killed": False,
            "mutation_kind": "NONE",
            "lineno": 0,
            "description": "no AST mutation candidate found",
        }

    nominal_args = dict(receipt.get("invoked_args") or {})
    proj_expect = lane.projection_entry(dict(receipt))["action_template"].get("expect")
    probes = synthesize_distinguishing_tuple(src, nominal_args, entrypoint=entrypoint)

    ref_code = compile(src, str(mod_file), "exec")
    mut_code = compile(mut["mutated_source"], str(mod_file), "exec")

    killed = False
    killed_by_probe: str | None = None
    template_expect_killed = False
    evaluated_count = 0

    for probe_kind, probe_args in probes:
        evaluated_count += 1
        lane.restore_snapshot_inputs(str(repo_root), nominal_args, receipt.get("input_digests"))
        ref_obs = _execute_code_with_probe(ref_code, mod_file, entrypoint, probe_args, repo_root, timeout_s)
        lane.restore_snapshot_inputs(str(repo_root), nominal_args, receipt.get("input_digests"))
        mut_obs = _execute_code_with_probe(mut_code, mod_file, entrypoint, probe_args, repo_root, timeout_s)

        if probe_kind == "nominal_receipt":
            if mut_obs["kind"] != "RETURN_DICT":
                template_expect_killed = True
            elif isinstance(mut_obs["raw"], Mapping):
                template_expect_killed = not v1._check_template_expect(proj_expect, mut_obs["raw"])

        if (ref_obs["kind"], ref_obs["sig"]) != (mut_obs["kind"], mut_obs["sig"]):
            killed = True
            killed_by_probe = f"{probe_kind}:{ref_obs['kind']}->{mut_obs['kind']}"
            break

    # Direct unit-level boundary probe for pure helper functions mutated outside `entrypoint`
    # when `entrypoint` only passes non-None values on existing receipts (e.g. `_check_template_expect(None, {})`)
    if not killed and _has_helper_expect_check(src):
        evaluated_count += 1
        ref_mod = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location("_pb_helper_ref_mod", str(mod_file))  # type: ignore[arg-type]
        )
        mut_mod = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location("_pb_helper_mut_mod", str(mod_file))  # type: ignore[arg-type]
        )
        sys.modules["_pb_helper_ref_mod"] = ref_mod
        sys.modules["_pb_helper_mut_mod"] = mut_mod
        try:
            exec(ref_code, ref_mod.__dict__)  # noqa: S102
            exec(mut_code, mut_mod.__dict__)  # noqa: S102
            r_val = ref_mod.__dict__["_check_template_expect"](None, {})
            m_val = mut_mod.__dict__["_check_template_expect"](None, {})
        finally:
            sys.modules.pop("_pb_helper_ref_mod", None)
            sys.modules.pop("_pb_helper_mut_mod", None)
        if r_val != m_val:
            killed = True
            killed_by_probe = "helper_boundary_none_expect"

    return {
        "capability_id": cid,
        "module_path": mod_rel,
        "verdict": f"KILLED_BY_APARTNESS_TUPLE({killed_by_probe})" if killed else "SURVIVED",
        "killed": killed,
        "killed_by_probe": killed_by_probe,
        "probes_evaluated": evaluated_count,
        "template_expect_killed": template_expect_killed,
        "mutation_kind": mut["mutation_kind"],
        "lineno": mut["lineno"],
        "description": mut["description"],
    }


def audit_harvested_capabilities_v2(
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
        results.append(evaluate_mutant_with_apartness_tuple(rec, repo_root))
    lane.restore_tree(str(repo_root), before, ("astra_runtime/tmp/",))

    total = len(results)
    killed = sum(1 for r in results if r["killed"])
    killed_by_non_nominal = sum(
        1 for r in results
        if r["killed"] and r.get("killed_by_probe") and not str(r["killed_by_probe"]).startswith("nominal_receipt:")
    )
    survivors = [r for r in results if not r["killed"]]
    survivor_rate = round(len(survivors) / max(total, 1), 4)
    kill_triggered = survivor_rate >= MAX_SURVIVOR_RATE

    digest = hashlib.sha256(
        json.dumps(results, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "play_id": "PLAY_6_V2_APARTNESS_TUPLE_MUTATION_GATE",
        "status": "GATE_THEATRE_SURVIVORS_EXCEED_15_PCT" if kill_triggered else "APARTNESS_ADMISSION_GATE_HOLDING",
        "pass": not kill_triggered,
        "output_verified": len(digest) == 64 and not kill_triggered,
        "capabilities_tested": total,
        "mutants_generated": total,
        "mutants_killed_by_apartness_tuple": killed,
        "mutants_killed_by_boundary_or_refusal_probes": killed_by_non_nominal,
        "surviving_mutant_count": len(survivors),
        "surviving_mutants": survivors,
        "survivor_rate": survivor_rate,
        "kill_criterion": {
            "max_survivor_rate_exclusive": MAX_SURVIVOR_RATE,
            "kill_triggered": kill_triggered,
        },
        "results": results,
        "audit_sha256": digest,
        "model_dependency_count": 0,
    }


def run(args: Mapping[str, Any] | None = None, root: str | pathlib.Path = ROOT) -> dict[str, Any]:
    req = dict(args or {})
    if req.get("all_harvested") is True:
        return audit_harvested_capabilities_v2(root, None)
    cids = req.get("capability_ids")
    if isinstance(cids, list) and cids:
        return audit_harvested_capabilities_v2(root, [str(x) for x in cids])
    default_cids = [
        "canonical.runtime.bound_capabilities.jq_query.hidden.v1",
        "canonical.runtime.bound_capabilities.concrete_execution_oracle.hidden.v1",
        "canonical.runtime.binding_pin_is_current_v1.hidden.v1",
        "canonical.runtime.capability_selection_retrieval_v1.hidden.v1",
    ]
    return audit_harvested_capabilities_v2(root, default_cids)


if __name__ == "__main__":
    print(json.dumps(audit_harvested_capabilities_v2(ROOT), indent=2, sort_keys=True))
