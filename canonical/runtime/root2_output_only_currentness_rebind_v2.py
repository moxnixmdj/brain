#!/usr/bin/env python3
"""Fail-closed currentness proof for restoring the verified 19-predicate Root2 DAG.

The prior output-only threshold DAG and its activation were independently
verified for the same 19 Root2-touching predicate set. A later LiveBench
forced-fail reclassification temporarily removed one predicate, but that
classification was revoked. This verifier permits scheduling-only rebind iff:

* the current Root2 predicate IDs are exactly the prior verified 19 IDs,
* Root1 has no current positive-gap predicate,
* acceptance/proof counts are unchanged,
* the predicate registry, evidence ledger, V17 frontier, DAG subject, and
  independent verification receipts are byte-identical to their verified
  bindings.

It grants no execution, promotion, fresh-reality, capability, or acceptance
credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ROOT2_OUTPUT_ONLY_CURRENTNESS_REBIND_V2"
ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "registry": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "evidence": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "root": "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "frontier_v17": "canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V17.json",
    "dag_manifest": "canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json",
    "dag_runtime": "canonical/runtime/threshold_proof_dag_v1.py",
    "dag_verification": "canonical/verification/ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
    "activation_v1": "canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_DAG_ACTIVATION_V1.json",
    "activation_verification": "canonical/verification/ROOT2_OUTPUT_ONLY_THRESHOLD_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}

EXPECTED_BLOBS = {
    "registry": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "evidence": "bc420c6d1a6caaab7a6d5c257640d3f5797170f5",
    "frontier_v17": "8c1325dd652b65a7d5c24e041ac06556a84f569c",
    "dag_manifest": "1fba51d15bcfdf6accd90948155517f7c9b98bbb",
    "dag_runtime": "7a0c715d931dbba05bc9e5ae344e1ead787ea5b8",
    "dag_verification": "553602570334f39003708e52d781b8c59f27eb7c",
    "activation_v1": "7ea4dd4edb59c8526bd3993e02f4a8fb53c65085",
    "activation_verification": "eef494009e47b758a99ab48649e050c332e4988a",
}

EXPECTED_COUNTS = {
    "accepted_families": 5,
    "open_families": 14,
    "proved_atomic": 12,
    "unresolved_atomic": 26,
}

EXPECTED_ROOT2_ONLY = {
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "CODING_CURSORBENCH_GE_57_8",
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_TB4_GE_66_4",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "HLE_TOOLS_GE_67_7",
    "LIVEBENCH_IF_GE_65_7",
    "MYSTERYMECHANISM_GE_49_55",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "PROWORK_GDPVAL_GE_1846",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
    "TB_SCIENCE_GE_58_7",
}

EXPECTED_MIXED = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}


class RebindError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _load_bytes(root: Path, rel: str) -> bytes:
    return (root / rel).read_bytes()


def _load_json(root: Path, rel: str) -> dict[str, Any]:
    return json.loads(_load_bytes(root, rel).decode("utf-8"))


def _unique_strings(value: Any, field: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise RebindError(field + "_INVALID")
    if len(value) != len(set(value)):
        raise RebindError(field + "_DUPLICATE")
    return set(value)


def evaluate(
    *,
    root_state: Mapping[str, Any],
    dag_manifest: Mapping[str, Any],
    dag_verification: Mapping[str, Any],
    activation: Mapping[str, Any],
    activation_verification: Mapping[str, Any],
    observed_blobs: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    for key, expected in EXPECTED_BLOBS.items():
        if observed_blobs.get(key) != expected:
            errors.append(f"BLOB_DRIFT:{key}:{observed_blobs.get(key)}:{expected}")

    current = root_state.get("current_acceptance")
    if not isinstance(current, Mapping):
        errors.append("CURRENT_ACCEPTANCE_MISSING")
        current = {}
    for key, expected in EXPECTED_COUNTS.items():
        if current.get(key) != expected:
            errors.append(f"COUNT_DRIFT:{key}:{current.get(key)}:{expected}")

    partition = root_state.get("current_residual_root_partition")
    if not isinstance(partition, Mapping):
        errors.append("CURRENT_RESIDUAL_ROOT_PARTITION_MISSING")
        partition = {}

    try:
        root2_only = _unique_strings(partition.get("root2_only"), "ROOT2_ONLY")
        mixed = _unique_strings(partition.get("root2_and_root3"), "ROOT2_AND_ROOT3")
        root1_only = _unique_strings(partition.get("root1_only"), "ROOT1_ONLY")
    except RebindError as exc:
        errors.append(str(exc))
        root2_only, mixed, root1_only = set(), set(), set()

    if root2_only != EXPECTED_ROOT2_ONLY:
        errors.append(
            "ROOT2_ONLY_SET_DRIFT:"
            + json.dumps(
                {
                    "missing": sorted(EXPECTED_ROOT2_ONLY - root2_only),
                    "extra": sorted(root2_only - EXPECTED_ROOT2_ONLY),
                },
                sort_keys=True,
            )
        )
    if mixed != EXPECTED_MIXED:
        errors.append(
            "ROOT2_AND_ROOT3_SET_DRIFT:"
            + json.dumps(
                {
                    "missing": sorted(EXPECTED_MIXED - mixed),
                    "extra": sorted(mixed - EXPECTED_MIXED),
                },
                sort_keys=True,
            )
        )
    if root1_only:
        errors.append("ROOT1_ONLY_NOT_EMPTY:" + ",".join(sorted(root1_only)))
    if partition.get("root1_positive_gap_count") != 0:
        errors.append("ROOT1_POSITIVE_GAP_COUNT_NOT_ZERO")
    if partition.get("unresolved_total") != 26:
        errors.append("UNRESOLVED_TOTAL_DRIFT")

    current_touching = root2_only | mixed
    if len(current_touching) != 19:
        errors.append(f"ROOT2_TOUCHING_COUNT:{len(current_touching)}")

    manifest_rows = dag_manifest.get("predicates")
    if not isinstance(manifest_rows, list):
        errors.append("DAG_PREDICATES_MISSING")
        manifest_ids: set[str] = set()
    else:
        raw_ids = [row.get("id") for row in manifest_rows if isinstance(row, Mapping)]
        if len(raw_ids) != len(manifest_rows) or any(not isinstance(x, str) or not x for x in raw_ids):
            errors.append("DAG_PREDICATE_ID_INVALID")
            manifest_ids = set()
        elif len(raw_ids) != len(set(raw_ids)):
            errors.append("DAG_PREDICATE_ID_DUPLICATE")
            manifest_ids = set(raw_ids)
        else:
            manifest_ids = set(raw_ids)

    if manifest_ids != current_touching:
        errors.append(
            "CURRENT_SET_NOT_EQUAL_VERIFIED_DAG:"
            + json.dumps(
                {
                    "missing_from_current": sorted(manifest_ids - current_touching),
                    "extra_in_current": sorted(current_touching - manifest_ids),
                },
                sort_keys=True,
            )
        )

    exact_state = dag_manifest.get("exact_state", {})
    expected_exact = {
        "accepted_families": 5,
        "open_families": 14,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "root2_only": 16,
        "root3_only": 7,
        "root2_and_root3": 3,
        "root2_touching": 19,
    }
    for key, expected in expected_exact.items():
        if exact_state.get(key) != expected:
            errors.append(f"DAG_EXACT_STATE_DRIFT:{key}:{exact_state.get(key)}:{expected}")

    if not str(dag_verification.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DAG_INDEPENDENT_VERIFICATION_NOT_PASS")
    verified = dag_verification.get("verified", {})
    if not isinstance(verified, Mapping) or verified.get("predicate_count") != 19:
        errors.append("DAG_VERIFIED_PREDICATE_COUNT_NOT_19")

    if activation.get("authority", {}).get("scheduling") is not True:
        errors.append("PRIOR_ACTIVATION_SCHEDULING_NOT_TRUE")
    for forbidden in ("execution", "promotion", "fresh_reality"):
        if activation.get("authority", {}).get(forbidden) is not False:
            errors.append(f"PRIOR_ACTIVATION_{forbidden.upper()}_NOT_FALSE")

    if not str(activation_verification.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ACTIVATION_INDEPENDENT_VERIFICATION_NOT_PASS")
    av = activation_verification.get("verified", {})
    if not isinstance(av, Mapping):
        errors.append("ACTIVATION_VERIFIED_BLOCK_MISSING")
        av = {}
    if av.get("root2_touching_predicates") != 19:
        errors.append("ACTIVATION_VERIFIED_ROOT2_COUNT_NOT_19")
    if av.get("root1_positive_gaps") != 0:
        errors.append("ACTIVATION_VERIFIED_ROOT1_NOT_ZERO")
    if av.get("fresh_reality_block_preserved") is not True:
        errors.append("ACTIVATION_FRESH_REALITY_BLOCK_NOT_VERIFIED")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_19_PREDICATE_STATE_IS_SEMANTICALLY_IDENTICAL_TO_INDEPENDENTLY_VERIFIED_OUTPUT_ONLY_DAG_ACTIVATION"
            if passed
            else "FAIL_CLOSED"
        ),
        "errors": errors,
        "current_root2_touching_predicates": sorted(current_touching),
        "current_root2_touching_count": len(current_touching),
        "verified_dag_predicates": sorted(manifest_ids),
        "semantic_identity_proved": passed and manifest_ids == current_touching,
        "unchanged_load_bearing_source_blobs_proved": passed,
        "scheduling_rebind_authorized": passed,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaim": (
            "THIS_RESTORES_ONLY_THE_PREVIOUSLY_VERIFIED_ROOT2_SCHEDULING_OVERLAY_FOR_AN_IDENTICAL_19_PREDICATE_STATE;"
            "IT_DOES_NOT_CLOSE_ANY_PREDICATE_OR_AUTHORIZE_FRESH_REALITY"
        ),
    }


def run(root: Path = ROOT) -> dict[str, Any]:
    observed = {}
    for key, rel in PATHS.items():
        if key == "root":
            continue
        observed[key] = git_blob_sha(_load_bytes(root, rel))

    return evaluate(
        root_state=_load_json(root, PATHS["root"]),
        dag_manifest=_load_json(root, PATHS["dag_manifest"]),
        dag_verification=_load_json(root, PATHS["dag_verification"]),
        activation=_load_json(root, PATHS["activation_v1"]),
        activation_verification=_load_json(root, PATHS["activation_verification"]),
        observed_blobs=observed,
    )


def main() -> None:
    out = run()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["status"].startswith("PASS__") else 1)


if __name__ == "__main__":
    main()
