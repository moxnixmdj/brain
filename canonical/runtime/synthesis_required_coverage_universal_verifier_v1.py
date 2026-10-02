"""Fail-closed universal proof for required-claim coverage in the exact Brain synthesis implementation.

This proves only an implementation property: every supported required claim reaching
solve_synthesis is retained in selected_claims on every successful return. It does
not prove Opus55 matched quality, and it does not transport the bound into the
frozen Opus55 target until an independent EXACT/SUPERSET scope relation exists.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/OPUS55_SYNTHESIS_REQUIRED_COVERAGE_UNIVERSAL_CANDIDATE_V1.json"
RUNTIME = ROOT / "canonical/runtime/contract_native_brain_candidate.py"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
BINDING_RECEIPT = ROOT / "canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

EXPECTED_RUNTIME_BLOB = "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85"
EXPECTED_REGISTRY_BLOB = "ee187f611a0e82b2de495ee377682f39bc31dd31"
EXPECTED_TARGETS_BLOB = "0910ce3a2351fc439e03a1fa2ae708fb3c6463ef"
EXPECTED_BINDING_RECEIPT_BLOB = "64ad40c1c10bd01e4c0f4418fac29efafea838fc"
BEHAVIOR = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
FAMILY = "COMMUNICATION_AND_SYNTHESIS"
TARGET = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(path.name + ":NOT_OBJECT")
    return value


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(hits) != 1:
        raise ValueError("FUNCTION_NOT_EXACTLY_ONE:" + name)
    return hits[0]


def _name_list_init(stmt: ast.stmt, names: set[str]) -> set[str]:
    found: set[str] = set()
    if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.List) or stmt.value.elts:
        return found
    for target in stmt.targets:
        if isinstance(target, ast.Tuple):
            for elt in target.elts:
                if isinstance(elt, ast.Name) and elt.id in names:
                    found.add(elt.id)
        elif isinstance(target, ast.Name) and target.id in names:
            found.add(target.id)
    return found


def _is_required_plus_optional(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
        and isinstance(node.left, ast.Name)
        and node.left.id == "required"
        and isinstance(node.right, ast.Name)
        and node.right.id == "optional"
    )


def _dict_value_for_key(node: ast.Dict, key: str) -> ast.AST | None:
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    out: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            out[child] = parent
    return out


def _nearest_if(node: ast.AST, parents: Mapping[ast.AST, ast.AST]) -> ast.If | None:
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, ast.If):
            return cur
    return None


def prove_runtime_structure(source: str) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    tree = ast.parse(source)
    fn = _function(tree, "solve_synthesis")
    parents = _parent_map(fn)

    initialized: set[str] = set()
    for stmt in fn.body:
        initialized |= _name_list_init(stmt, {"required", "optional", "uncertainty"})
    if initialized != {"required", "optional", "uncertainty"}:
        errors.append("LIST_INITIALIZATION_NOT_EXACT")

    required_assignments = [
        n for n in ast.walk(fn)
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        and any(
            isinstance(t, ast.Name) and t.id == "required"
            for t in (
                n.targets if isinstance(n, ast.Assign)
                else [n.target]
            )
        )
    ]
    if len(required_assignments) != 1:
        errors.append("REQUIRED_REASSIGNED_OR_NOT_INITIALIZED_ONCE")

    required_method_calls = []
    for n in ast.walk(fn):
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "required"
        ):
            required_method_calls.append(n)
    append_calls = [n for n in required_method_calls if n.func.attr == "append"]
    if len(append_calls) != 1 or len(required_method_calls) != 1:
        errors.append("REQUIRED_MUTATION_SET_NOT_EXACT_SINGLE_APPEND")
    else:
        call = append_calls[0]
        if len(call.args) != 1 or not isinstance(call.args[0], ast.Name) or call.args[0].id != "cid":
            errors.append("REQUIRED_APPEND_NOT_CID")
        guard = _nearest_if(call, parents)
        expected_guard = "role == 'required' and support != 'unsupported'"
        if guard is None or ast.unparse(guard.test) != expected_guard:
            errors.append("REQUIRED_APPEND_GUARD_NOT_EXACT")

    alias_assignments = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Name) and n.value.id == "required":
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id != "required":
                    alias_assignments.append(t.id)
    if alias_assignments:
        errors.append("REQUIRED_ESCAPES_BY_ALIAS")

    selected_assignments = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "selected" for t in n.targets):
                selected_assignments.append(n)
    if len(selected_assignments) != 2 or any(not _is_required_plus_optional(n.value) for n in selected_assignments):
        errors.append("SELECTED_NOT_ALWAYS_REQUIRED_PLUS_OPTIONAL")

    optional_slice_assignments = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "optional" for t in n.targets):
            if not isinstance(n.value, ast.List):
                optional_slice_assignments.append(n)
    if len(optional_slice_assignments) != 1:
        errors.append("OPTIONAL_BUDGET_MUTATION_NOT_EXACT_SINGLE_ASSIGNMENT")
    else:
        v = optional_slice_assignments[0].value
        if not (
            isinstance(v, ast.Subscript)
            and isinstance(v.value, ast.Name)
            and v.value.id == "optional"
            and isinstance(v.slice, ast.Slice)
        ):
            errors.append("OPTIONAL_BUDGET_MUTATION_NOT_SLICE")

    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
    if len(returns) != 1 or not isinstance(returns[0].value, ast.Dict):
        errors.append("RETURN_SHAPE_NOT_EXACT_SINGLE_DICT")
    else:
        selected_value = _dict_value_for_key(returns[0].value, "selected_claims")
        if not isinstance(selected_value, ast.Name) or selected_value.id != "selected":
            errors.append("RETURNED_SELECTED_CLAIMS_NOT_SELECTED")

    theorem = {
        "required_definition": "role == required AND support != unsupported",
        "required_append_count": len(append_calls),
        "required_other_mutation_count": max(0, len(required_method_calls) - len(append_calls)),
        "required_alias_count": len(alias_assignments),
        "selected_assignment_count": len(selected_assignments),
        "selected_assignments_all_required_plus_optional": bool(selected_assignments) and all(
            _is_required_plus_optional(n.value) for n in selected_assignments
        ),
        "optional_only_budget_truncation": len(optional_slice_assignments) == 1,
        "returned_selected_claims_is_selected": not any(e == "RETURNED_SELECTED_CLAIMS_NOT_SELECTED" for e in errors),
    }
    return (not errors, sorted(set(errors)), theorem)


def evaluate(
    candidate: Mapping[str, Any],
    registry: Mapping[str, Any],
    targets: Mapping[str, Any],
    binding_receipt: Mapping[str, Any],
    *,
    source_shas: Mapping[str, str],
    runtime_source: str,
) -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        "runtime": EXPECTED_RUNTIME_BLOB,
        "registry": EXPECTED_REGISTRY_BLOB,
        "targets": EXPECTED_TARGETS_BLOB,
        "binding_receipt": EXPECTED_BINDING_RECEIPT_BLOB,
    }
    for key, sha in expected.items():
        if source_shas.get(key) != sha:
            errors.append("SOURCE_BLOB_DRIFT:" + key)

    auth = candidate.get("authority")
    if not isinstance(auth, Mapping):
        errors.append("AUTHORITY_MISSING")
    else:
        checks = {
            "candidate_runtime": ("canonical/runtime/contract_native_brain_candidate.py", EXPECTED_RUNTIME_BLOB),
            "behavioral_contract_registry": ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", EXPECTED_REGISTRY_BLOB),
            "target_normalization": ("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json", EXPECTED_TARGETS_BLOB),
            "independent_atom_binding": ("canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json", EXPECTED_BINDING_RECEIPT_BLOB),
        }
        for key, (path, sha) in checks.items():
            row = auth.get(key)
            if not isinstance(row, Mapping) or row.get("path") != path or row.get("git_blob_sha") != sha:
                errors.append("AUTHORITY_MISMATCH:" + key)

    rows = registry.get("active_contracted_residuals")
    contract = next(
        (x for x in rows if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR),
        None,
    ) if isinstance(rows, list) else None
    if not isinstance(contract, Mapping):
        errors.append("SYNTHESIS_CONTRACT_MISSING")
    else:
        if "Verified evidence units" not in str(contract.get("inputs") or ""):
            errors.append("CONTRACT_INPUT_NOT_VERIFIED_EVIDENCE")
        if "required coverage is complete" not in str(contract.get("success_condition") or ""):
            errors.append("CONTRACT_SUCCESS_DOES_NOT_REQUIRE_COMPLETE_COVERAGE")

    fmap = registry.get("family_to_residual_contracts")
    if not isinstance(fmap, Mapping) or fmap.get(FAMILY) != [BEHAVIOR]:
        errors.append("SYNTHESIS_FAMILY_NOT_SINGLETON_CONTRACT")

    target_rows = targets.get("targets")
    target = next(
        (x for x in target_rows if isinstance(x, Mapping) and x.get("predicate_id") == TARGET),
        None,
    ) if isinstance(target_rows, list) else None
    if not isinstance(target, Mapping):
        errors.append("TARGET_NORMALIZATION_MISSING")
    else:
        atoms = {
            x.get("atom")
            for x in target.get("atom_sources", [])
            if isinstance(x, Mapping)
        }
        if "metric:required_claim_coverage" not in atoms:
            errors.append("TARGET_REQUIRED_COVERAGE_ATOM_MISSING")
        metrics = {
            x.get("metric")
            for x in target.get("metric_requirement_sources", [])
            if isinstance(x, Mapping)
        }
        if "required_claim_coverage_noninferiority" not in metrics:
            errors.append("TARGET_REQUIRED_COVERAGE_METRIC_REQUIREMENT_MISSING")

    if not str(binding_receipt.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ATOM_BINDING_NOT_INDEPENDENT_PASS")
    if binding_receipt.get("numeric_metric_bounds_verified") is not False:
        errors.append("BASELINE_BINDING_MUST_NOT_ALREADY_CLAIM_NUMERIC_BOUND")
    if "metric:matched_quality" not in set(binding_receipt.get("remaining_target_atoms") or []):
        errors.append("MATCHED_QUALITY_RESIDUAL_NOT_PRESERVED")
    exact = binding_receipt.get("exact_brain_blobs")
    if not isinstance(exact, Mapping) or exact.get(
        "canonical/governance/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_CANDIDATE_V1.json"
    ) != "a988b6fa4baf1d753f709c757c97f17185181f0a":
        errors.append("ATOM_BINDING_CANDIDATE_PROVENANCE_DRIFT")

    proof_ok, proof_errors, theorem = prove_runtime_structure(runtime_source)
    errors.extend(proof_errors)

    lemma = candidate.get("lemma")
    if not isinstance(lemma, Mapping):
        errors.append("LEMMA_MISSING")
    else:
        if lemma.get("lower_bound") != 1.0 or lemma.get("theoretical_upper_bound") != 1.0:
            errors.append("LEMMA_BOUND_NOT_CEILING_ONE")
        if lemma.get("property") != "EVERY_REQUIRED_CLAIM_ID_IS_PRESENT_IN_RETURNED_SELECTED_CLAIMS":
            errors.append("LEMMA_PROPERTY_DRIFT")

    transport = candidate.get("target_transport")
    if not isinstance(transport, Mapping):
        errors.append("TARGET_TRANSPORT_MISSING")
    else:
        if transport.get("acceptance_metric_bound_authorized") is not False:
            errors.append("TARGET_SCOPE_TRANSPORT_MUST_REMAIN_UNAUTHORIZED")
        bound = transport.get("universal_brain_metric_bound_candidate")
        if not isinstance(bound, Mapping) or bound.get("brain_lower_bound") != 1.0 or bound.get("theoretical_upper_bound") != 1.0:
            errors.append("CANDIDATE_BOUND_INVALID")

    if errors or not proof_ok:
        return {
            "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_REQUIRED_COVERAGE_UNIVERSAL_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": sorted(set(errors)),
            "universal_required_coverage_proved": False,
            "target_scope_transport_authorized": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "new_reality_units_consumed": 0,
        }

    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_REQUIRED_COVERAGE_UNIVERSAL_VERDICT_V1",
        "status": "PASS__UNIVERSAL_REQUIRED_COVERAGE_CEILING_PROVED_FOR_EXACT_BRAIN_CONTRACT__TARGET_SCOPE_TRANSPORT_OPEN__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "behavior_id": BEHAVIOR,
        "target_predicate_id": TARGET,
        "universal_required_coverage_proved": True,
        "proof_scope": "ALL_VALID_EXECUTIONS_OF_EXACT_SOLVE_SYNTHESIS_REACHING_RETURN",
        "brain_required_claim_coverage_lower_bound": 1.0,
        "theoretical_upper_bound": 1.0,
        "theorem_structure": theorem,
        "target_scope_transport_authorized": False,
        "remaining_acceptance_blockers": [
            "INDEPENDENT_EXACT_OR_SUPERSET_SYNTHESIS_TARGET_SCOPE_RELATION",
            "metric:matched_quality",
            "matched_quality_noninferiority",
        ],
        "rule": "UNIVERSAL_IMPLEMENTATION_LEMMA_REPLACES_FINITE_SAMPLE_UNCERTAINTY_FOR_REQUIRED_COVERAGE__NO_CROSS_SCOPE_NONINFERIORITY_WITHOUT_VERIFIED_SCOPE_RELATION",
        "new_reality_units_consumed": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    docs = (
        _load(CANDIDATE),
        _load(REGISTRY),
        _load(TARGETS),
        _load(BINDING_RECEIPT),
    )
    out = evaluate(
        *docs,
        source_shas={
            "runtime": _blob(RUNTIME),
            "registry": _blob(REGISTRY),
            "targets": _blob(TARGETS),
            "binding_receipt": _blob(BINDING_RECEIPT),
        },
        runtime_source=RUNTIME.read_text(encoding="utf-8"),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
