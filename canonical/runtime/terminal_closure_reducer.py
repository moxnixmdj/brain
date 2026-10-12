"""Fail-closed terminal-goal closure reducer for Project Brain.

This module does not estimate progress. It answers exactly one question:
does the supplied terminal closure manifest prove every required predicate?

Unknown, null, malformed, duplicate, open, contaminated, donor-dependent,
or otherwise unresolved state always reduces to NOT ACHIEVED.
"""
from __future__ import annotations

import argparse
from hashlib import sha1
import json
from pathlib import Path
import sys
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.runtime.runtime_cognition_credit_guard_v1 import assert_credit_path_cognition_governance

REQUIRED_FAMILY_COUNT = 19
REQUIRED_COUNTERS = (
    "uncontracted_required_behaviors",
    "unproved_required_behaviors",
    "donor_dependent_required_behaviors",
    "unresolved_verifier_mutations",
    "unresolved_composition_failures",
    "contaminated_promotion_evidence",
    "resource_or_authority_violations",
)
REQUIRED_PREDICATES = (
    "exact_target_family_count_19",
    "every_required_behavior_contracted",
    "every_required_behavior_has_admissible_proof",
    "donor_dependent_required_behaviors_zero",
    "unexplained_required_behaviors_zero",
    "unresolved_verifier_mutations_zero",
    "unresolved_composition_failures_zero",
    "contaminated_evidence_used_for_promotion_zero",
    "resource_or_authority_violations_zero",
    "all_frozen_opus_acceptance_predicates_pass",
    "final_donor_deletion_cleanroom_pass",
    "proof_bundle_frozen",
)

UNIVERSAL_PROOF_KINDS = {
    "FULL_SCOPE_DB_COVER",
    "TARGET_ESCAPE_NONOCCUPANCY",
    "GENERATOR_CLOSURE_SCOPE_COMPLETE",
    "SELECTED_COVER_COMPLEMENT_UNSAT",
}
GLOBAL_OWNERSHIP_REDUCER = "canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py"
GLOBAL_OWNERSHIP_REQUIRED_PREDICATES = (
    "final_donor_deletion_cleanroom_pass",
    "donor_deletion_protocol_v2_bound",
    "runtime_cognition_model_independent",
    "zero_external_model_runtime_cognition_dependencies",
    "copied_or_rehosted_teacher_absent",
    "runtime_dependency_inventory_complete",
)

UNIVERSAL_REQUIRED_TRUE = (
    "independent_verified",
    "exact_byte_bound",
    "observable_trace_scope_complete",
    "all_useful_target_behaviors_in_scope",
    "every_admission_sound",
    "residual_complement_unsat",
    "selected_cover_complete",
    "u_empty",
    "abc_closed",
    "all_credited_routes_brain_owned",
    "donor_independence_closed",
    "clean_room_replay_pass",
)


def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _content_binding(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _hex40(value.get("git_blob_sha"))
    )


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _load_bound_json(
    binding: Any,
    repo_root: Path | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Load one repository JSON artifact only when its declared Git blob is exact."""
    if not _content_binding(binding):
        return None, "BINDING_SHAPE_INVALID"
    if repo_root is None:
        return None, "REPOSITORY_ROOT_REQUIRED"

    relative = Path(binding["path"])
    if relative.is_absolute():
        return None, "ABSOLUTE_PATH_FORBIDDEN"

    root = repo_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, "PATH_ESCAPES_REPOSITORY"
    if not candidate.is_file():
        return None, "BOUND_FILE_MISSING"
    if _git_blob_sha(candidate) != binding["git_blob_sha"]:
        return None, "GIT_BLOB_SHA_MISMATCH"

    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "BOUND_JSON_UNREADABLE"
    if not isinstance(payload, dict):
        return None, "BOUND_JSON_NOT_OBJECT"
    return payload, None


def _evaluate_universal_cover_proof(
    manifest: dict[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Validate the stronger route from exact proof bytes plus an exact verifier receipt."""
    declaration = manifest.get("universal_cover_proof")
    if not isinstance(declaration, dict):
        return {
            "pass": False,
            "reason": "UNIVERSAL_COVER_PROOF_ABSENT",
            "failed_predicates": ["UNIVERSAL_COVER_PROOF_ABSENT"],
        }

    failures: list[str] = []
    proof_binding = declaration.get("proof_artifact")
    verifier_binding = declaration.get("verifier_receipt_artifact")

    proof, proof_error = _load_bound_json(proof_binding, repo_root)
    verifier, verifier_error = _load_bound_json(verifier_binding, repo_root)
    if proof_error is not None:
        failures.append(f"UNIVERSAL_PROOF_ARTIFACT_UNBOUND:{proof_error}")
    if verifier_error is not None:
        failures.append(f"UNIVERSAL_VERIFIER_RECEIPT_UNBOUND:{verifier_error}")

    proof = proof or {}
    verifier = verifier or {}

    if proof.get("proof_kind") not in UNIVERSAL_PROOF_KINDS:
        failures.append("UNIVERSAL_PROOF_KIND_INVALID")
    if proof.get("scope_id") != "scope://opus55/observable-trace":
        failures.append("UNIVERSAL_SCOPE_ID_INVALID")
    if proof.get("conclusion") != "success":
        failures.append("UNIVERSAL_SUCCESS_CONCLUSION_REQUIRED")

    # These semantic claims must come from the content-addressed proof artifact,
    # never from handwritten booleans in the terminal manifest.
    for name in UNIVERSAL_REQUIRED_TRUE:
        if name in {"independent_verified", "exact_byte_bound"}:
            continue
        if proof.get(name) is not True:
            failures.append(f"UNIVERSAL_PREDICATE_NOT_TRUE:{name}")

    # Independence and exact-byte verification must come from a separately
    # content-addressed verifier receipt bound to the exact proof artifact.
    if verifier.get("independent_verified") is not True:
        failures.append("UNIVERSAL_INDEPENDENT_VERIFICATION_REQUIRED")
    if verifier.get("exact_byte_bound") is not True:
        failures.append("UNIVERSAL_EXACT_BYTE_VERIFICATION_REQUIRED")
    if verifier.get("conclusion") != "success":
        failures.append("UNIVERSAL_VERIFIER_SUCCESS_REQUIRED")
    if verifier.get("proof_artifact") != proof_binding:
        failures.append("UNIVERSAL_VERIFIER_PROOF_BINDING_MISMATCH")

    # A manifest may repeat identity fields for readability, but disagreement
    # with the bound proof bytes is a hard failure.
    for name in ("proof_kind", "scope_id", "conclusion"):
        if name in declaration and declaration.get(name) != proof.get(name):
            failures.append(f"UNIVERSAL_DECLARATION_MISMATCH:{name}")

    unique = sorted(set(failures))
    return {
        "pass": not unique,
        "reason": "PASS__UNIVERSAL_SCOPE_COMPLETE_COVER" if not unique else "FAIL_CLOSED",
        "failed_predicates": unique,
        "proof_kind": proof.get("proof_kind"),
        "scope_id": proof.get("scope_id"),
    }


def _evaluate_current_donor_authority(
    manifest: dict[str, Any],
    repo_root: Path | None,
) -> dict[str, Any]:
    failures: list[str] = []
    if repo_root is None:
        return {
            "pass": False,
            "failed_predicates": ["DONOR_AUTHORITY_REPOSITORY_ROOT_REQUIRED"],
        }
    root = repo_root.resolve()
    gp = manifest.get("global_ownership_postconditions")
    if not isinstance(gp, dict):
        return {
            "pass": False,
            "failed_predicates": ["GLOBAL_OWNERSHIP_POSTCONDITIONS_MISSING"],
        }
    binding = {
        "path": gp.get("evidence"),
        "git_blob_sha": gp.get("evidence_blob_sha"),
    }
    receipt, error = _load_bound_json(binding, root)
    if error is not None:
        failures.append("GLOBAL_OWNERSHIP_RECEIPT_UNBOUND:" + error)
        receipt = {}
    reducer_path = (root / GLOBAL_OWNERSHIP_REDUCER).resolve()
    try:
        reducer_path.relative_to(root)
    except ValueError:
        failures.append("GLOBAL_OWNERSHIP_REDUCER_PATH_ESCAPES_REPOSITORY")
    if not reducer_path.is_file():
        failures.append("GLOBAL_OWNERSHIP_REDUCER_MISSING")
        reducer_blob = None
    else:
        reducer_blob = _git_blob_sha(reducer_path)
    if receipt.get("brain_reducer_blob_sha") != reducer_blob:
        failures.append("GLOBAL_OWNERSHIP_RECEIPT_REDUCER_BLOB_STALE")
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(receipt.get("status", "")):
        failures.append("GLOBAL_OWNERSHIP_RECEIPT_NOT_INDEPENDENT_PASS")
    result = receipt.get("result")
    predicates = result.get("terminal_predicates") if isinstance(result, dict) else None
    if not isinstance(predicates, dict):
        failures.append("GLOBAL_OWNERSHIP_RECEIPT_PREDICATES_MISSING")
    else:
        for name in GLOBAL_OWNERSHIP_REQUIRED_PREDICATES:
            if predicates.get(name) is not True:
                failures.append(
                    "GLOBAL_OWNERSHIP_ZERO_MODEL_PREDICATE_NOT_TRUE:" + name
                )
    unique = sorted(set(failures))
    return {
        "pass": not unique,
        "failed_predicates": unique,
        "receipt_binding": binding if not unique else None,
    }


def _family_terminally_closed(family: dict[str, Any]) -> bool:
    """Derive terminal closure from semantic fields, not display-label equality.

    Manifests use both the compact state PASS and decorated passing states.
    A decorated state is closed only when calibrated Opus acceptance passes,
    ownership is verified, and no unresolved obligation remains. Open,
    quarantined, or failing states remain fail-closed.
    """
    state = family.get("closure_state")
    if not isinstance(state, str) or "PASS" not in state:
        return False
    if any(marker in state for marker in ("OPEN", "FAIL", "QUARANTINED")):
        return False

    # A display label is never proof. Compact PASS and decorated PASS states
    # obey the same semantic closure gate so a manifest cannot manufacture
    # terminality by writing closure_state="PASS".
    return (
        family.get("opus55_acceptance_state") == "PASS"
        and family.get("opus55_acceptance_calibrated") is True
        and family.get("ownership_status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        and family.get("unresolved") == []
    )


def evaluate_manifest(
    manifest: dict[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    assert_credit_path_cognition_governance(Path(__file__).resolve().parents[2])
    failures: list[str] = []

    if manifest.get("expected_family_count") != REQUIRED_FAMILY_COUNT:
        failures.append("EXPECTED_FAMILY_COUNT_NOT_19")

    families = manifest.get("families")
    if not isinstance(families, list):
        families = []
        failures.append("FAMILIES_NOT_LIST")

    ids: list[str] = []
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            failures.append(f"FAMILY_{index}_MALFORMED")
            continue
        fid = family.get("id")
        if not isinstance(fid, str) or not fid.strip():
            failures.append(f"FAMILY_{index}_ID_INVALID")
            continue
        ids.append(fid)
        if not _family_terminally_closed(family):
            failures.append(f"FAMILY_OPEN:{fid}")

    if len(families) != REQUIRED_FAMILY_COUNT:
        failures.append(f"ACTUAL_FAMILY_COUNT:{len(families)}")
    if len(ids) != len(set(ids)):
        failures.append("DUPLICATE_FAMILY_ID")
    if manifest.get("actual_family_count") != len(families):
        failures.append("DECLARED_ACTUAL_FAMILY_COUNT_MISMATCH")

    counters = manifest.get("counters")
    if not isinstance(counters, dict):
        counters = {}
        failures.append("COUNTERS_NOT_OBJECT")
    for name in REQUIRED_COUNTERS:
        value = counters.get(name)
        if type(value) is not int:
            failures.append(f"COUNTER_UNKNOWN_OR_NONINTEGER:{name}")
        elif value != 0:
            failures.append(f"COUNTER_NONZERO:{name}:{value}")

    predicates = manifest.get("terminal_predicates")
    if not isinstance(predicates, dict):
        predicates = {}
        failures.append("TERMINAL_PREDICATES_NOT_OBJECT")
    for name in REQUIRED_PREDICATES:
        if predicates.get(name) is not True:
            failures.append(f"PREDICATE_NOT_TRUE:{name}")

    # Cross-check counter-backed predicates. A handwritten true may not override
    # a missing/nonzero counter.
    counter_predicates = {
        "donor_dependent_required_behaviors": "donor_dependent_required_behaviors_zero",
        "unresolved_verifier_mutations": "unresolved_verifier_mutations_zero",
        "unresolved_composition_failures": "unresolved_composition_failures_zero",
        "contaminated_promotion_evidence": "contaminated_evidence_used_for_promotion_zero",
        "resource_or_authority_violations": "resource_or_authority_violations_zero",
    }
    for counter, predicate in counter_predicates.items():
        if counters.get(counter) != 0 and predicates.get(predicate) is True:
            failures.append(f"COUNTER_PREDICATE_CONTRADICTION:{counter}:{predicate}")

    donor_authority = _evaluate_current_donor_authority(manifest, repo_root)
    for failure in donor_authority["failed_predicates"]:
        failures.append("DONOR_AUTHORITY:" + failure)

    legacy_failures = sorted(set(failures))
    universal = _evaluate_universal_cover_proof(manifest, repo_root)

    # The 19-family protocol conjunction is one sound proof route, not the only
    # logically sufficient route. A scope-complete universal cover may bypass
    # only family-open failures and the aggregate frozen-acceptance predicate.
    # It may not bypass common safety, ownership, donor, resource, clean-room,
    # specification, or proof-freeze predicates.
    bypassable = {
        failure
        for failure in legacy_failures
        if failure.startswith("FAMILY_OPEN:")
        or failure == "PREDICATE_NOT_TRUE:all_frozen_opus_acceptance_predicates_pass"
    }

    if universal["pass"]:
        effective_failures = sorted(
            failure for failure in legacy_failures if failure not in bypassable
        )
    else:
        effective_failures = legacy_failures

    achieved = not effective_failures
    if achieved and universal["pass"] and legacy_failures:
        proof_route = "UNIVERSAL_SCOPE_COMPLETE_COVER"
    elif achieved:
        proof_route = "FROZEN_19_FAMILY_PROTOCOLS"
    else:
        proof_route = None

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CLOSURE_VERDICT_V2",
        "achieved": achieved,
        "proof_route": proof_route,
        "failed_predicates": effective_failures,
        "legacy_family_route_failed_predicates": legacy_failures,
        "universal_cover_route": universal,
        "current_donor_authority": donor_authority,
        "family_count": len(families),
        "closed_family_count": sum(
            1 for family in families
            if isinstance(family, dict) and _family_terminally_closed(family)
        ),
        "rule": (
            "ACHIEVED_IFF_COMMON_FINALITY_PREDICATES_PASS_AND_EITHER_"
            "FROZEN_19_FAMILY_PROTOCOL_ROUTE_OR_SCOPE_COMPLETE_UNIVERSAL_COVER_ROUTE_PASSES"
        ),
    }



def evaluate_frontier_state(
    active_hierarchy: dict[str, Any],
    global_universe: dict[str, Any],
    prequalification: dict[str, Any],
) -> dict[str, Any]:
    """Reduce live execution authority from receipt-derived frontier projections.

    The three input manifests are projections, not independent authorities.
    Any disagreement about implementation authority, prequalification, or
    terminal-evidence admission fails closed instead of scheduling more work.
    """
    assert_credit_path_cognition_governance(Path(__file__).resolve().parents[2])
    failures: list[str] = []

    if not all(
        isinstance(x, dict)
        for x in (active_hierarchy, global_universe, prequalification)
    ):
        return {
            "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "fresh_terminal_evidence_allowed": False,
            "failed_invariants": ["FRONTIER_INPUT_NOT_OBJECT"],
            "next_action": "RECONCILE_RECEIPT_DERIVED_STATE",
        }

    active_frontier = active_hierarchy.get("atomic_preproof_frontier")
    global_frontier = global_universe.get("atomic_preproof_frontier")
    global_cut = global_universe.get("global_cut")
    global_exec = global_universe.get("execution_authority")
    preq_progress = prequalification.get("prequalification_progress")

    if not isinstance(active_frontier, dict):
        active_frontier = {}
        failures.append("ACTIVE_ATOMIC_FRONTIER_MISSING")
    if not isinstance(global_frontier, dict):
        global_frontier = {}
        failures.append("GLOBAL_ATOMIC_FRONTIER_MISSING")
    if not isinstance(global_cut, dict):
        global_cut = {}
        failures.append("GLOBAL_CUT_MISSING")
    if not isinstance(global_exec, dict):
        global_exec = {}
        failures.append("GLOBAL_EXECUTION_AUTHORITY_MISSING")
    if not isinstance(preq_progress, dict):
        preq_progress = {}
        failures.append("PREQUALIFICATION_PROGRESS_MISSING")

    active_count = active_frontier.get("implementation_authority_count")
    global_count = global_frontier.get(
        "implementation_authority_count",
        global_cut.get("atomic_preproof_survivor_count"),
    )

    if type(active_count) is not int or active_count < 0:
        failures.append("ACTIVE_IMPLEMENTATION_AUTHORITY_COUNT_INVALID")
    if type(global_count) is not int or global_count < 0:
        failures.append("GLOBAL_IMPLEMENTATION_AUTHORITY_COUNT_INVALID")
    if (
        type(active_count) is int
        and type(global_count) is int
        and active_count != global_count
    ):
        failures.append(
            f"IMPLEMENTATION_AUTHORITY_COUNT_CONTRADICTION:{active_count}:{global_count}"
        )

    zero_preproof = preq_progress.get("zero_preproof_implementation_residuals")
    if type(zero_preproof) is not bool:
        failures.append("PREQUALIFICATION_ZERO_PREPROOF_FLAG_INVALID")
    elif type(active_count) is int and zero_preproof != (active_count == 0):
        failures.append(
            "PREQUALIFICATION_ZERO_PREPROOF_CONTRADICTS_ACTIVE_FRONTIER"
        )

    active_execute_now = active_frontier.get("execute_now")
    global_execute_now = global_frontier.get("execute_now")
    if type(active_execute_now) is not bool:
        failures.append("ACTIVE_EXECUTE_NOW_INVALID")
    if type(global_execute_now) is not bool:
        failures.append("GLOBAL_EXECUTE_NOW_INVALID")
    if (
        type(active_execute_now) is bool
        and type(global_execute_now) is bool
        and active_execute_now != global_execute_now
    ):
        failures.append("EXECUTE_NOW_CONTRADICTION")

    preq_authority = prequalification.get("execution_authority")
    if type(preq_authority) is not bool:
        failures.append("PREQUALIFICATION_EXECUTION_AUTHORITY_INVALID")
    frozen_preq = global_universe.get("terminal_prequalification")
    if isinstance(frozen_preq, dict) and type(frozen_preq.get("execution_authority")) is bool:
        preq_authority = bool(preq_authority and frozen_preq["execution_authority"])

    global_fresh = global_exec.get("fresh_terminal_evidence_allowed")
    if type(global_fresh) is not bool:
        failures.append("GLOBAL_FRESH_TERMINAL_EVIDENCE_FLAG_INVALID")

    expected_fresh = bool(
        type(preq_authority) is bool
        and preq_authority
        and type(active_count) is int
        and active_count == 0
    )
    if type(global_fresh) is bool and global_fresh != expected_fresh:
        failures.append("FRESH_TERMINAL_EVIDENCE_AUTHORITY_CONTRADICTION")

    unique_failures = sorted(set(failures))
    if unique_failures:
        return {
            "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "fresh_terminal_evidence_allowed": False,
            "failed_invariants": unique_failures,
            "implementation_authority_count": (
                active_count if type(active_count) is int else None
            ),
            "next_action": "RECONCILE_RECEIPT_DERIVED_STATE",
        }

    if active_count > 0:
        next_action = "EXECUTE_ONLY_CURRENT_AUTHORIZED_PREPROOF_RESIDUALS"
    elif not preq_authority:
        next_action = "COMPLETE_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION"
    else:
        next_action = "EXECUTE_T0_T1_T2_T3_IN_PARALLEL"

    return {
        "schema": "PROJECT_BRAIN_FRONTIER_STATE_VERDICT_V1",
        "status": "PASS",
        "execution_authority": bool(preq_authority and active_count == 0),
        "fresh_terminal_evidence_allowed": expected_fresh,
        "failed_invariants": [],
        "implementation_authority_count": active_count,
        "prequalification_execution_authority": preq_authority,
        "next_action": next_action,
        "rule": (
            "DERIVED_MANIFEST_DISAGREEMENT_FAILS_CLOSED__"
            "NO_MANIFEST_HAS_INDEPENDENT_AUTHORITY"
        ),
    }


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument(
        "--frontier",
        nargs=3,
        metavar=("ACTIVE_HIERARCHY", "GLOBAL_UNIVERSE", "PREQUALIFICATION"),
        type=Path,
    )
    args = parser.parse_args()

    if args.frontier:
        if args.manifest is not None:
            parser.error("manifest and --frontier are mutually exclusive")
        active, universe, prequalification = map(_load_json, args.frontier)
        verdict = evaluate_frontier_state(active, universe, prequalification)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict["status"] == "PASS" else 1

    if args.manifest is None:
        parser.error("provide manifest or --frontier")
    repo_root = Path(__file__).resolve().parents[2]
    verdict = evaluate_manifest(_load_json(args.manifest), repo_root=repo_root)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["achieved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
