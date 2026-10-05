"""Static closed-world audit of the model-independent composition controller.

This verifier grants no acceptance credit. It answers a narrower question needed
by the live Composition P1/P2 proof route: is the controller dispatch surface
finite and exactly enumerated, and which actions can mutate durable state or
delegate to effectful machinery?

The audit fails closed. Detecting a durable effect is not the same as proving
rollback. A stateful action becomes proof-eligible only after a separate,
scope-complete contract establishes immutable/content-addressed output,
transactional restoration, or verified compensating rollback for every
load-bearing effect.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME = ROOT / "canonical" / "runtime" / "astra_runtime.py"

LOCAL_MUTATOR_ATTRS = {
    "write_text", "write_bytes", "mkdir", "unlink", "rename",
    "replace", "rmdir", "touch",
}
DELEGATE_NAMES = {"_invoke_bound_capability"}
PROCESS_NAMES = {"subprocess.run", "subprocess.Popen", "os.system"}

WITNESS_SPECS = {
    "invoke_capability_until": {
        "required_names": {"attempts_dir", "attempt_json", "attempt_png"},
        "effect": "ATTEMPTS_DIRECTORY_TREE",
        "missing_capture_key": "attempts_dir",
    },
    "invoke_capability_fanout": {
        "required_names": {"output_dir", "manifest_path"},
        "effect": "FANOUT_ARTIFACT_SET",
        "missing_capture_key": "output_dir",
    },
}


class AuditError(ValueError):
    pass


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    parts: list[str] = []
    cur: ast.AST = fn
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AuditError("FUNCTION_MISSING:" + name)


def _allowed_types(run_fn: ast.FunctionDef) -> set[str]:
    for node in ast.walk(run_fn):
        if isinstance(node, ast.Assign):
            if not any(
                isinstance(t, ast.Name) and t.id == "allowed_types"
                for t in node.targets
            ):
                continue
            if isinstance(node.value, (ast.Set, ast.List, ast.Tuple)):
                vals = {
                    elt.value
                    for elt in node.value.elts
                    if isinstance(elt, ast.Constant)
                    and isinstance(elt.value, str)
                }
                if vals:
                    return vals
    raise AuditError("ALLOWED_TYPES_LITERAL_SET_MISSING")


def _typ_literal(test: ast.AST) -> str | None:
    if (
        not isinstance(test, ast.Compare)
        or len(test.ops) != 1
        or len(test.comparators) != 1
        or not isinstance(test.ops[0], ast.Eq)
    ):
        return None
    left, right = test.left, test.comparators[0]
    if (
        isinstance(left, ast.Name)
        and left.id == "typ"
        and isinstance(right, ast.Constant)
        and isinstance(right.value, str)
    ):
        return right.value
    if (
        isinstance(right, ast.Name)
        and right.id == "typ"
        and isinstance(left, ast.Constant)
        and isinstance(left.value, str)
    ):
        return left.value
    return None


def _implemented_branches(goal_fn: ast.FunctionDef) -> dict[str, ast.If]:
    out: dict[str, ast.If] = {}
    for node in goal_fn.body:
        if not isinstance(node, ast.If):
            continue
        typ = _typ_literal(node.test)
        if typ is None:
            continue
        if typ in out:
            raise AuditError("DUPLICATE_ACTION_BRANCH:" + typ)
        out[typ] = node
    if not out:
        raise AuditError("NO_ACTION_BRANCHES")
    return out


def _effect_features(branch: ast.If) -> dict[str, Any]:
    calls: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(branch):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name:
                calls.add(name)
        elif isinstance(node, ast.Name):
            names.add(node.id)

    local_mutators = sorted(
        name for name in calls
        if name.rsplit(".", 1)[-1] in LOCAL_MUTATOR_ATTRS
    )
    delegated = sorted(name for name in calls if name in DELEGATE_NAMES)
    process = sorted(name for name in calls if name in PROCESS_NAMES)
    recursive_goal = "_goal_action" in calls

    if delegated or process:
        effect_class = "DELEGATED_OR_PROCESS_EFFECT"
    elif local_mutators:
        effect_class = "LOCAL_DURABLE_MUTATION"
    elif recursive_goal:
        effect_class = "RECURSIVE_EFFECT_REQUIRES_TRANSITIVE_PROOF"
    else:
        effect_class = "NO_DIRECT_DURABLE_MUTATION_OBSERVED"

    return {
        "effect_class": effect_class,
        "calls": sorted(calls),
        "local_mutators": local_mutators,
        "delegated_calls": delegated,
        "process_calls": process,
        "recursive_goal_call": recursive_goal,
        "names": sorted(names),
    }


def _capture_keys(capture_fn: ast.FunctionDef) -> set[str]:
    strings = {
        node.value
        for node in ast.walk(capture_fn)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    return {
        s for s in strings
        if s.endswith("_path") or s in {"xlsx_path", "screenshot_path"}
    }


def audit_runtime(path: str | Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    goal_fn = _function(tree, "_goal_action")
    run_fn = _function(tree, "_run_model_independent_goal")
    capture_fn = _function(tree, "_controller_durable_paths")

    allowed = _allowed_types(run_fn)
    branches = _implemented_branches(goal_fn)
    implemented = set(branches)
    capture_keys = _capture_keys(capture_fn)

    rows: dict[str, Any] = {}
    raw_features: dict[str, dict[str, Any]] = {}
    for typ in sorted(implemented):
        features = _effect_features(branches[typ])
        raw_features[typ] = features
        rows[typ] = {k: v for k, v in features.items() if k != "names"}

    witnesses: list[dict[str, Any]] = []
    for typ, spec in WITNESS_SPECS.items():
        branch = branches.get(typ)
        if branch is None:
            continue
        names = set(raw_features[typ]["names"])
        if not set(spec["required_names"]).issubset(names):
            continue
        missing_key = str(spec["missing_capture_key"])
        if missing_key in capture_keys:
            continue
        witnesses.append({
            "action_type": typ,
            "effect": spec["effect"],
            "reason": (
                "ACTION_CREATES_OR_OWNS_DURABLE_EFFECT_OUTSIDE_"
                "CURRENT_TOP_LEVEL_CAPTURE_KEYS"
            ),
            "missing_capture_key": missing_key,
        })

    exact_dispatch = allowed == implemented
    stateful = sorted(
        typ for typ, row in rows.items()
        if row["effect_class"] != "NO_DIRECT_DURABLE_MUTATION_OBSERVED"
    )
    delegated = sorted(
        typ for typ, row in rows.items()
        if row["effect_class"] == "DELEGATED_OR_PROCESS_EFFECT"
    )
    local_write = sorted(
        typ for typ, row in rows.items()
        if row["effect_class"] == "LOCAL_DURABLE_MUTATION"
    )

    unresolved_effect_actions = sorted(set(stateful))

    return {
        "schema": "PROJECT_BRAIN_COMPOSITION_CONTROLLER_EFFECT_SURFACE_AUDIT_V1",
        "runtime_path": str(path),
        "status": (
            "FAIL_CLOSED__NO_BYPASS_NOT_PROVED"
            if unresolved_effect_actions or witnesses or not exact_dispatch
            else "PASS__FINITE_EFFECT_SURFACE_CLOSED"
        ),
        "allowed_action_count": len(allowed),
        "implemented_action_count": len(implemented),
        "dispatch_surface_exact": exact_dispatch,
        "allowed_not_implemented": sorted(allowed - implemented),
        "implemented_not_allowed": sorted(implemented - allowed),
        "capture_path_keys": sorted(capture_keys),
        "effect_classes": rows,
        "stateful_action_types": stateful,
        "delegated_or_process_action_types": delegated,
        "local_durable_mutation_action_types": local_write,
        "uncovered_effect_witnesses": witnesses,
        "unresolved_effect_action_types": unresolved_effect_actions,
        "global_p1_p2_no_bypass_proved": (
            exact_dispatch and not unresolved_effect_actions and not witnesses
        ),
        "proof_rule": (
            "DETECTION_OR_HASHING_ALONE_IS_NOT_ROLLBACK. "
            "EACH_LOAD_BEARING_STATEFUL_ACTION_REQUIRES_SCOPE_COMPLETE_"
            "IMMUTABLE_CONTENT_ADDRESSED_OUTPUT_OR_TRANSACTIONAL_RESTORATION_"
            "OR_VERIFIED_COMPENSATING_ROLLBACK_BEFORE_P1_P2_CREDIT."
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    result = audit_runtime()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["dispatch_surface_exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
