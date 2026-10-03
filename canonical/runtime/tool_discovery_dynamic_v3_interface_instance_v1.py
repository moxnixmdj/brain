"""Content-addressed complete-interface instance proof for Tool Discovery Dynamic V3.

Narrow claim only: the already-frozen Dynamic V3 proof harness is one concrete
finite discovery-interface instance satisfying the seven properties in
TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.

This does NOT claim the six-class frozen harness exhausts every open-domain tool
ecosystem. Whole-protocol scope remains a separate acceptance-reduction question.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_V3_INTERFACE_INSTANCE_V1"

PROOF = "canonical/runtime/tool_discovery_dynamic_proof_v3.py"
CANDIDATE = "canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
REFINEMENT_VERIFICATION = (
    "canonical/verification/"
    "TOOL_DISCOVERY_DYNAMIC_REFINEMENT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
)

EXPECTED = {
    PROOF: "f82d949f3890ffc0f2513f9b39cc3585a5d22ebb",
    CANDIDATE: "bbbee4d6baf8df937543644397abba38a67dce62",
    CONTRACT: "49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    REFINEMENT_VERIFICATION: "5fcdc5ae35f51c40f312edbe5727284c9f6ca3dd",
}

REQUIRED = {
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _generator_shape_errors() -> list[str]:
    """Prove the exact bound generator has six semantic variants, not seed variants."""
    source = (ROOT / PROOF).read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "generate_case"
        ),
        None,
    )
    if fn is None:
        return ["GENERATE_CASE_NOT_FOUND"]

    errors: list[str] = []
    cls_assignment = False
    r_loads = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "cls":
                    text = ast.unparse(node.value)
                    if text == "CLASSES[ordinal % len(CLASSES)]":
                        cls_assignment = True
        if isinstance(node, ast.Name) and node.id == "r" and isinstance(node.ctx, ast.Load):
            r_loads += 1

    if not cls_assignment:
        errors.append("CLASS_SELECTION_NOT_EXACT_MODULO_CLASSES")
    if r_loads != 0:
        errors.append("RANDOM_STATE_IS_SEMANTICALLY_LOAD_BEARING")
    if tuple(proof.CLASSES) != (
        "DYNAMIC_DISCOVERY",
        "GENERIC_CONSTRAINT",
        "MULTI_SOURCE",
        "TRANSFER",
        "VERSION_CHANGE",
        "NO_ROUTE",
    ):
        errors.append("FROZEN_CLASS_SET_DRIFT")
    return errors


def _case_signature(case: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in case.items() if k != "case_id"}


def _case_errors(case: dict[str, Any]) -> tuple[list[str], dict[str, bool]]:
    errors: list[str] = []
    props = {key: True for key in REQUIRED}

    tools = case.get("tools")
    sources = case.get("discovery_sources")
    initial = case.get("initial_visible")
    if not isinstance(tools, list) or not isinstance(sources, list) or not isinstance(initial, list):
        return ["CASE_INTERFACE_SHAPE_INVALID"], {key: False for key in REQUIRED}

    tool_ids = [str(t.get("tool_id") or "") for t in tools if isinstance(t, dict)]
    source_ids = [str(s.get("source_id") or "") for s in sources if isinstance(s, dict)]
    if (
        len(tool_ids) != len(tools)
        or not all(tool_ids)
        or len(set(tool_ids)) != len(tool_ids)
        or len(source_ids) != len(sources)
        or not all(source_ids)
        or len(set(source_ids)) != len(source_ids)
    ):
        props["FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH"] = False
        errors.append("FINITE_SOURCE_OR_TOOL_IDENTITY_INVALID")

    byid = {str(t["tool_id"]): t for t in tools}
    visible = set(map(str, initial))
    authoritative_union = set(visible)

    for source in sources:
        sid = str(source.get("source_id") or "")
        if source.get("available") is not True:
            errors.append("FROZEN_INSTANCE_SOURCE_NOT_AVAILABLE:" + sid)
            props["UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"] = False
            continue

        declared = [str(x) for x in source.get("tool_ids") or []]
        if any(tid not in byid for tid in declared):
            errors.append("SOURCE_REFERENCES_UNKNOWN_TOOL:" + sid)
            props["UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"] = False
            continue

        before = set(visible)
        try:
            receipt = proof._discover(case, sid, "CAP_A")
        except Exception as exc:  # pragma: no cover - fail-closed path
            errors.append("DISCOVERY_EXECUTION_FAILED:" + sid + ":" + type(exc).__name__)
            props["DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE"] = False
            props["DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH"] = False
            props["DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS"] = False
            continue

        if receipt.get("kind") != "DISCOVERY_RESULT" or receipt.get("source_id") != sid:
            props["DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE"] = False
            errors.append("DISCOVERY_RECEIPT_SOURCE_MISMATCH:" + sid)

        rec_tools = receipt.get("tools")
        if not isinstance(rec_tools, list):
            rec_tools = []
        rec_ids = [str(t.get("tool_id") or "") for t in rec_tools if isinstance(t, dict)]
        visible.update(rec_ids)
        if not before <= visible or len(visible) < len(before):
            props["DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH"] = False
            errors.append("DISCOVERY_NOT_MONOTONIC:" + sid)

        if set(rec_ids) != set(declared):
            props["UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"] = False
            errors.append("DISCOVERY_RESULT_IDENTITY_SET_DRIFT:" + sid)

        for item in rec_tools:
            if not isinstance(item, dict):
                props["DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS"] = False
                errors.append("DISCOVERED_TOOL_NOT_OBJECT:" + sid)
                continue
            tid = str(item.get("tool_id") or "")
            expected = proof._public_tool(byid[tid]) if tid in byid else None
            if expected is None or item != expected:
                props["DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS"] = False
                errors.append("DISCOVERED_METADATA_NOT_EXACT:" + sid + ":" + tid)

        authoritative_union.update(declared)

    if authoritative_union != set(tool_ids):
        props["UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE"] = False
        errors.append(
            "AUTHORITATIVE_UNION_INCOMPLETE:"
            + ",".join(sorted(set(tool_ids) - authoritative_union))
        )

    for stage in (1, 2):
        first_epochs = proof._epoch_map(case, stage)
        second_epochs = proof._epoch_map(case, stage)
        if first_epochs != second_epochs:
            props["VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE"] = False
            errors.append(f"EPOCH_MAP_UNSTABLE_WITHIN_STAGE:{stage}")

        oracle_key = "epoch0" if stage == 1 else "epoch1"
        oracle = case.get("_oracle", {}).get(oracle_key, {})
        for tid in tool_ids:
            try:
                receipt = proof._probe(case, stage, tid, "CAP_A")
            except Exception as exc:  # pragma: no cover - fail-closed path
                props["SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND"] = False
                errors.append("PROBE_FAILED:" + tid + ":" + str(stage) + ":" + type(exc).__name__)
                continue
            if (
                receipt.get("kind") != "SAFE_CAPABILITY_PROBE"
                or receipt.get("tool_id") != tid
                or receipt.get("capability") != "CAP_A"
                or receipt.get("epoch") != first_epochs.get(tid)
                or receipt.get("supported") is not bool(oracle.get(tid))
            ):
                props["SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND"] = False
                errors.append("PROBE_RECEIPT_NOT_TRUTHFUL_EPOCH_BOUND:" + tid + ":" + str(stage))

    e1 = proof._epoch_map(case, 1)
    e2 = proof._epoch_map(case, 2)
    changed = {tid for tid in tool_ids if e1.get(tid) != e2.get(tid)}
    if case.get("case_class") == "VERSION_CHANGE":
        if changed != {"T1"} or e1.get("T1") != 0 or e2.get("T1") != 1:
            props["VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE"] = False
            errors.append("VERSION_CHANGE_NOT_EXACT_T1_EPOCH_TRANSITION")
    elif changed:
        props["VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE"] = False
        errors.append("UNDECLARED_CROSS_STAGE_EPOCH_CHANGE")

    return errors, props


def evaluate() -> dict[str, Any]:
    drift = [path for path, sha in EXPECTED.items() if _blob_sha(path) != sha]
    if drift:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_BLOB_DRIFT:" + x for x in drift],
            "instance_verified_candidate": False,
            "whole_protocol_scope_proved": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    contract = _load(CONTRACT)
    required = contract.get("required_properties")
    if not isinstance(required, list) or set(required) != REQUIRED:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["INTERFACE_CONTRACT_PROPERTIES_DRIFT"],
            "instance_verified_candidate": False,
            "whole_protocol_scope_proved": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    errors = _generator_shape_errors()
    all_props = {key: True for key in REQUIRED}
    signatures: dict[str, dict[str, Any]] = {}

    # Exact semantic classes are ordinal mod 6. Seed is non-semantic because the
    # generator's random state is never loaded; these two seed values act as a
    # regression check on top of the AST proof, not as the proof itself.
    for ordinal, class_name in enumerate(proof.CLASSES):
        case0 = proof.generate_case(0, ordinal)
        case1 = proof.generate_case(2**63 - 1, ordinal)
        if _case_signature(case0) != _case_signature(case1):
            errors.append("SEED_AFFECTS_INTERFACE_SEMANTICS:" + class_name)
        if case0.get("case_class") != class_name:
            errors.append("CLASS_GENERATION_DRIFT:" + class_name)
        case_errors, props = _case_errors(case0)
        errors.extend(class_name + ":" + e for e in case_errors)
        for key, value in props.items():
            all_props[key] = all_props[key] and value
        signatures[class_name] = {
            "tool_ids": sorted(str(t["tool_id"]) for t in case0["tools"]),
            "initial_visible": sorted(map(str, case0["initial_visible"])),
            "sources": {
                str(s["source_id"]): sorted(map(str, s["tool_ids"]))
                for s in case0["discovery_sources"]
            },
        }

    for key, value in all_props.items():
        if not value:
            errors.append("CONTRACT_PROPERTY_FAILED:" + key)

    passed = not errors and all(all_props.values())
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CONTENT_ADDRESSED_FROZEN_INTERFACE_INSTANCE_SATISFIES_CONTRACT__"
            "INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
            if passed
            else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "interface_instance_id": "TOOL_DISCOVERY_DYNAMIC_V3_FROZEN_HARNESS_INTERFACE_INSTANCE_V1",
        "declared_target_scope": "EXACT_DYNAMIC_V3_FROZEN_SIX_CLASS_GENERATOR_INTERFACE",
        "semantic_variant_count": len(proof.CLASSES),
        "semantic_variants": list(proof.CLASSES),
        "instance_signatures": signatures,
        "required_properties": {key: all_props[key] for key in sorted(REQUIRED)},
        "instance_verified_candidate": passed,
        "whole_protocol_scope_proved": False,
        "whole_protocol_scope_nonclaim": (
            "THIS_INSTANCE_ESTABLISHES_ONE_REAL_COMPLETE_INTERFACE_INSTANCE_ONLY;"
            " IT_DOES_NOT_PROVE_THE_SIX_CLASS_HARNESS_EXHAUSTS_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS."
        ),
        "next_if_independently_verified": (
            "RUN_SEPARATE_TOOL_DISCOVERY_ACCEPTANCE_SCOPE_REDUCTION_AGAINST_THE_FROZEN_PROTOCOL;"
            " DO_NOT_GRANT_ACCEPTANCE_FROM_THIS_INSTANCE_PROOF_ALONE."
        ),
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
