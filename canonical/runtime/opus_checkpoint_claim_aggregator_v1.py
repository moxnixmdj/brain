"""Claim-scoped Opus 5.5 checkpoint aggregator (issue #3743).

Compiles the current load-bearing Opus checkpoint obligation basis from
current terminal authority (never inheriting a historical count as an
axiom), freezes each obligation as a CHECKPOINT_ACCEPTANCE claim under the
#3730 canonical claim core, deduplicates logical aliases only with an
explicit necessity/equivalence proof, and emits a content-addressed
checkpoint manifest with an explicit scope-completeness theorem.

Aggregate checkpoint completion holds iff the manifest is proved
scope-complete AND every required claim is sound and satisfied under the
same frozen checkpoint epoch. GLOBAL_OPEN_ENDED_MISSION_COMPLETE stays
non-derivable: checkpoint completion is not mission completion. Fail
closed everywhere; zero spend; zero terminal credit.
"""

from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.runtime.coverage_claim_scope_guard_v1 import (
    compute_claim_id,
    validate_claim,
)
from canonical.runtime.terminal_closure_reducer import (
    REQUIRED_FAMILY_COUNT,
    _family_terminally_closed,
    evaluate_manifest,
)
from canonical.runtime.terminal_reality_gate_v1 import MANDATORY_SEMANTICS

ROOT = Path(__file__).resolve().parents[2]

TERMINAL_AUTHORITY_PATH = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MISSION_PATH = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
CLOSURE_MANIFEST_REL = "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
REGISTRY_REL = "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"
EMITTED_MANIFEST_REL = "canonical/governance/OPUS_CHECKPOINT_CLAIM_MANIFEST_V1.json"

CLAIM_KIND = "CHECKPOINT_ACCEPTANCE"
SCHEMA = "PROJECT_BRAIN_OPUS_CHECKPOINT_CLAIM_MANIFEST_V1"
EPOCH_PREFIX = "OPUS_CHECKPOINT_EPOCH_V1"
AUTHORITY_PREFIX = "TERMINAL_CLOSURE_MANIFEST_V1::CC_R4_PROOF_AUTHORITY_V1"

SCOPE_COMPLETENESS_THEOREM = (
    "THE_CHECKPOINT_CLAIM_SET_COVERS_EXACTLY_THE_RECOMPUTED_CURRENT_LOAD_BEARING_"
    "OPUS_CHECKPOINT_OBLIGATION_BASIS__EVERY_FAMILY_OF_THE_CURRENT_TERMINAL_"
    "CLOSURE_MANIFEST_AND_EVERY_REFINEMENT_FAMILY_OF_THE_CURRENT_RESIDUAL_MAP_"
    "EACH_EXACTLY_ONCE__NO_EXTRA_CLAIM__NO_MISSING_REQUIREMENT__ALL_ACCEPTANCE_"
    "REQUIREMENTS_PRESERVED__PROVED_BY_BASIS_PARTITION_EQUALITY_AND_CLAIM_SET_"
    "IDENTITY_UNDER_ONE_FROZEN_CHECKPOINT_EPOCH"
)
GLOBAL_MISSION_COMPLETION_NON_DERIVABLE = True
ZERO_CREDIT = 0


class CheckpointAggregationError(RuntimeError):
    """Raised fail-closed on any basis, binding, alias, or theorem violation."""


def _fail(reason: str) -> None:
    raise CheckpointAggregationError(reason)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:  # fail closed on any read/parse failure
        raise CheckpointAggregationError(f"SOURCE_READ_FAILED:{path}:{exc}") from exc
    if not isinstance(data, dict):
        raise CheckpointAggregationError(f"SOURCE_NOT_OBJECT:{path}")
    return data


def _require(condition: Any, reason: str) -> None:
    if not condition:
        _fail(reason)


def _require_hex40(value: Any, label: str) -> str:
    ok = isinstance(value, str) and len(value) == 40 and all(
        ch in "0123456789abcdef" for ch in value
    )
    if not ok:
        _fail(f"INVALID_GIT_BLOB_SHA:{label}")
    return value


def _bound_source(binding: Any, label: str) -> Path:
    """Resolve a terminal-authority pin to a path after exact blob verification."""
    _require(isinstance(binding, Mapping), f"SOURCE_BINDING_NOT_OBJECT:{label}")
    rel = binding.get("path")
    _require(isinstance(rel, str) and rel.endswith(".json"), f"SOURCE_BINDING_PATH_INVALID:{label}")
    _require_hex40(binding.get("git_blob_sha"), label)
    path = (ROOT / rel).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        _fail(f"SOURCE_BINDING_PATH_ESCAPES_REPOSITORY:{label}")
    _require(path.is_file(), f"BOUND_SOURCE_MISSING:{label}:{rel}")
    actual = _git_blob_sha(path)
    _require(
        actual == binding["git_blob_sha"],
        f"SOURCE_PIN_STALE:{label}:pinned={binding['git_blob_sha']}:actual={actual}",
    )
    return path


def _family_scope_core(family: Mapping[str, Any], preserved: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family_id": family.get("id"),
        "target_behavior": family.get("target_behavior"),
        "acceptance_basis": family.get("acceptance_basis"),
        "proof_bundle": family.get("proof_bundle"),
        "preserved_residual_requirements": preserved.get("residuals"),
        "preserved_residual_mode": preserved.get("mode"),
        "mandatory_terminal_semantics": MANDATORY_SEMANTICS,
    }


def _compile_claim(
    family: Mapping[str, Any],
    preserved: Mapping[str, Any],
    *,
    epoch: str,
    mission_blob_sha: str,
    authority_id: str,
    semantics_core: Mapping[str, Any],
) -> dict[str, Any]:
    scope_core = _family_scope_core(family, preserved)
    claim = {
        "claim_kind": CLAIM_KIND,
        "mission_blob_sha": mission_blob_sha,
        "scope_sha256": _sha256(_canonical_json(scope_core)),
        "target_predicate_sha256": _sha256(
            f"FAMILY_{family.get('id')}::{MANDATORY_SEMANTICS}"
        ),
        "semantics_sha256": _sha256(_canonical_json(dict(semantics_core))),
        "epoch": epoch,
        "authority_id": authority_id,
        "terminal_credit_delta": ZERO_CREDIT,
    }
    claim["claim_id"] = compute_claim_id(claim)
    verdict = validate_claim(claim, current_mission_blob_sha=mission_blob_sha)
    _require(verdict.get("pass") is True, f"CLAIM_CORE_INVALID:{family.get('id')}:{verdict.get('errors')}")
    return claim


def _satisfied(family: Mapping[str, Any]) -> bool:
    return (
        family.get("opus55_acceptance_state") == "PASS"
        and family.get("opus55_acceptance_calibrated") is True
        and _family_terminally_closed(family)
    )


def _claim_status(family: Mapping[str, Any]) -> str:
    if _satisfied(family):
        return "SATISFIED__ACCEPTANCE_PASS_AND_TERMINALLY_CLOSED"
    if family.get("opus55_acceptance_state") != "PASS" or family.get("opus55_acceptance_calibrated") is not True:
        return "OPEN__OPUS55_ACCEPTANCE_PROTOCOL_RESULT_OPEN"
    return "OPEN__TERMINAL_CLOSURE_PREDICATE_OPEN"


def compile_checkpoint_aggregate() -> dict[str, Any]:
    """Recompute the current obligation basis and freeze it as claim instances."""
    # 1. Current terminal authority (root, unpinned by construction).
    authority_path = ROOT / TERMINAL_AUTHORITY_PATH
    authority = _load_json(authority_path)
    authority_blob = _git_blob_sha(authority_path)
    live = authority.get("live_truth") or {}
    sources = authority.get("authoritative_sources") or {}

    # 2. Current mission binding for the claim core.
    mission_path = ROOT / MISSION_PATH
    _require(mission_path.is_file(), "MISSION_POINTER_MISSING")
    mission_blob_sha = _git_blob_sha(mission_path)

    # 3. Current closure manifest via exact terminal-authority pin.
    manifest_path = _bound_source(
        sources.get("terminal_closure_manifest_current"), "terminal_closure_manifest_current"
    )
    closure_manifest = _load_json(manifest_path)
    closure_manifest_blob = _git_blob_sha(manifest_path)

    # 4. Current residual map via exact terminal-authority pin.
    residual_path = _bound_source(
        sources.get("abc_zero_reality_fixed_point_v3"), "abc_zero_reality_fixed_point_v3"
    )
    residual_map = _load_json(residual_path)
    residual_blob = _git_blob_sha(residual_path)

    # 5. R4 proof authority: registry bound by r4_live_binding_currentness.
    r4 = authority.get("r4_live_binding_currentness") or {}
    registry_sha = _require_hex40(r4.get("root_registry_sha"), "r4_root_registry_sha")
    registry_path = (ROOT / REGISTRY_REL).resolve()
    _require(registry_path.is_file(), "REGISTRY_MISSING")
    _require(
        _git_blob_sha(registry_path) == registry_sha,
        "R4_REGISTRY_BINDING_STALE",
    )
    registry = _load_json(registry_path)
    _require(
        r4.get("property_scoped_r4_proof_closure") is True,
        "R4_PROOF_CLOSURE_NOT_CURRENT",
    )
    open_roots = r4.get("current_root_certificates_open")
    _require(
        isinstance(open_roots, int) and open_roots == 0,
        "R4_ROOT_CERTIFICATES_OPEN",
    )

    # 6. Recompute the obligation basis from current rows (no historical axiom).
    families = closure_manifest.get("families")
    _require(isinstance(families, list) and bool(families), "CLOSURE_MANIFEST_FAMILIES_INVALID")
    manifest_ids: list[str] = []
    for index, family in enumerate(families):
        _require(isinstance(family, Mapping) and isinstance(family.get("id"), str) and family["id"].strip(),
                 f"BASIS_FAMILY_MALFORMED:{index}")
        manifest_ids.append(family["id"])
    _require(len(manifest_ids) == len(set(manifest_ids)), "BASIS_DUPLICATE_FAMILY_ID")

    open_rows = residual_map.get("open_refinements")
    _require(isinstance(open_rows, list), "RESIDUAL_OPEN_REFINEMENTS_INVALID")
    closed_ids = residual_map.get("closed_ABC_refinements")
    _require(isinstance(closed_ids, list), "RESIDUAL_CLOSED_REFINEMENTS_INVALID")
    residual_open = {row.get("family"): row for row in open_rows if isinstance(row, Mapping)}
    residual_closed = {x for x in closed_ids if isinstance(x, str)}
    double_listed = sorted(set(residual_open) & residual_closed)
    _require(not double_listed, f"RESIDUAL_FAMILY_DOUBLE_LISTED:{double_listed}")
    residual_ids = set(residual_open) | residual_closed

    basis_ids = sorted(set(manifest_ids) | residual_ids)
    only_manifest = sorted(set(manifest_ids) - residual_ids)
    only_residual = sorted(residual_ids - set(manifest_ids))
    _require(
        not only_manifest and not only_residual,
        f"BASIS_PARTITION_MISMATCH:only_manifest={only_manifest}:only_residual={only_residual}",
    )

    # Consistency checks against independently declared current counts.
    _require(
        len(basis_ids) == REQUIRED_FAMILY_COUNT,
        f"BASIS_FAMILY_COUNT_MISMATCH:{len(basis_ids)}!={REQUIRED_FAMILY_COUNT}",
    )
    declared_partition = int(live.get("L1_refinement_partition_count") or -1)
    _require(
        declared_partition == len(basis_ids),
        f"LIVE_PARTITION_COUNT_MISMATCH:{declared_partition}!={len(basis_ids)}",
    )
    _require(
        closure_manifest.get("expected_family_count") == len(basis_ids)
        and closure_manifest.get("actual_family_count") == len(families),
        "CLOSURE_MANIFEST_COUNT_FIELDS_INCONSISTENT",
    )

    # 7. Frozen checkpoint epoch over the exact bound sources.
    epoch = (
        f"{EPOCH_PREFIX}__"
        + _sha256(
            "|".join(
                [
                    mission_blob_sha,
                    authority_blob,
                    closure_manifest_blob,
                    residual_blob,
                    registry_sha,
                ]
            )
        )[:16]
    )
    authority_id = f"{AUTHORITY_PREFIX}__{registry_sha[:12]}"
    semantics_core = {
        "mandatory_terminal_semantics": MANDATORY_SEMANTICS,
        "verdict_rule": closure_manifest.get("verdict_rule"),
        "reducer": "canonical/runtime/terminal_closure_reducer.py",
        "acceptance_calibration": closure_manifest.get("acceptance_calibration"),
        "claim_scope_law": "canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json",
    }

    # 8. Compile claims; aliases deduplicated only with an equivalence proof.
    claims: list[dict[str, Any]] = []
    alias_proofs: list[dict[str, Any]] = []
    claim_ids_seen: dict[str, str] = {}
    for family in sorted(families, key=lambda f: str(f.get("id"))):
        fid = family["id"]
        preserved = residual_open.get(fid) or {}
        # Equivalence proof for the manifest/residual alias of this family.
        in_manifest = fid in set(manifest_ids)
        in_residual = fid in residual_ids
        if in_manifest and in_residual:
            alias_proofs.append(
                {
                    "family_id": fid,
                    "logical_alias_sources": [
                        "TERMINAL_CLOSURE_MANIFEST_V1",
                        "ABC_ZERO_REALITY_FIXED_POINT_RESIDUAL_MAP_V3",
                    ],
                    "equivalence_proof": (
                        "SAME_FAMILY_IDENTITY_ACROSS_BOTH_CURRENT_PINNED_BASIS_SOURCES_"
                        "AND_SINGLE_FROZEN_SCOPE_CORE_PRESERVING_EVERY_UNDERLYING_"
                        "ACCEPTANCE_REQUIREMENT_FROM_BOTH_SOURCES"
                    ),
                    "preserved_requirements": {
                        "residuals": preserved.get("residuals"),
                        "mode": preserved.get("mode"),
                        "acceptance_basis": family.get("acceptance_basis"),
                    },
                }
            )
        claim = _compile_claim(
            family,
            preserved,
            epoch=epoch,
            mission_blob_sha=mission_blob_sha,
            authority_id=authority_id,
            semantics_core=semantics_core,
        )
        prior = claim_ids_seen.get(claim["claim_id"])
        if prior is not None:
            has_proof = any(p["family_id"] == fid for p in alias_proofs)
            _require(
                has_proof and prior == fid,
                f"ALIAS_WITHOUT_EQUIVALENCE_PROOF:{prior}:{fid}",
            )
            continue
        claim_ids_seen[claim["claim_id"]] = fid
        claims.append(
            {
                "family_id": fid,
                "claim": claim,
                "claim_status": _claim_status(family),
                "satisfied": _satisfied(family),
                "r4_proof_authority": {
                    "authority_id": authority_id,
                    "root_registry_git_blob_sha": registry_sha,
                    "active_claim_id": r4.get("active_claim"),
                    "r4_closure": r4.get("status"),
                },
            }
        )

    claim_id_set = [row["claim"]["claim_id"] for row in claims]
    # Claim-set identity with the recomputed basis (bijective on families).
    _require(
        {row["family_id"] for row in claims} == set(basis_ids)
        and len(claims) == len(basis_ids),
        "CLAIM_SET_NOT_BIJECTIVE_WITH_BASIS",
    )

    # 9. Aggregate under the frozen reducer truth.
    closure = evaluate_manifest(closure_manifest, repo_root=ROOT)
    closure_achieved = closure.get("achieved") is True
    all_satisfied = all(row["satisfied"] for row in claims)
    scope_complete = True  # reached only through the fail-closed checks above
    checkpoint_complete = bool(scope_complete and all_satisfied and closure_achieved)

    satisfied_count = sum(1 for row in claims if row["satisfied"])
    return {
        "schema": SCHEMA,
        "date": "2026-10-13",
        "checkpoint_objective": authority.get("checkpoint_objective"),
        "epoch": epoch,
        "frozen_checkpoint_epoch_sources": {
            "mission_pointer_git_blob_sha": mission_blob_sha,
            "terminal_authority_git_blob_sha": authority_blob,
            "terminal_closure_manifest_git_blob_sha": closure_manifest_blob,
            "residual_map_git_blob_sha": residual_blob,
            "coverage_root_certificate_registry_git_blob_sha": registry_sha,
        },
        "recomputed_obligation_basis": {
            "basis_family_count": len(basis_ids),
            "basis_family_ids": basis_ids,
            "manifest_family_count": len(manifest_ids),
            "residual_map_family_count": len(residual_ids),
            "basis_partition_equality_proved": True,
            "consistency_checks": {
                "terminal_closure_reducer_required_family_count": REQUIRED_FAMILY_COUNT,
                "live_L1_refinement_partition_count": declared_partition,
                "closure_manifest_expected_family_count": closure_manifest.get("expected_family_count"),
            },
            "alias_deduplication_policy": "LOGICAL_ALIASES_DEDUPLICATED_ONLY_WITH_NECESSITY_EQUIVALENCE_PROOF",
            "alias_equivalence_proofs": alias_proofs,
        },
        "scope_completeness_theorem": {
            "statement": SCOPE_COMPLETENESS_THEOREM,
            "proved": scope_complete,
            "proof_basis": "FAIL_CLOSED_RECOMPUTATION_OF_BASIS_FROM_BOTH_CURRENT_PINNED_SOURCES_WITH_PARTITION_EQUALITY_AND_BIJECTIVE_CLAIM_SET",
        },
        "claims": claims,
        "aggregate": {
            "required_claim_count": len(claims),
            "satisfied_claim_count": satisfied_count,
            "open_claim_count": len(claims) - satisfied_count,
            "scope_complete": scope_complete,
            "all_required_claims_sound": True,
            "reducer_closure_achieved": closure_achieved,
            "reducer_failed_predicates": closure.get("failed_predicates", []),
            "checkpoint_complete": checkpoint_complete,
            "aggregation_rule": (
                "CHECKPOINT_COMPLETE_IFF_MANIFEST_SCOPE_COMPLETE_AND_EVERY_REQUIRED_"
                "CLAIM_SOUND_AND_SATISFIED_UNDER_THE_SAME_FROZEN_CHECKPOINT_EPOCH"
            ),
            "global_open_ended_mission_complete": False,
            "global_mission_completion_derivable": False,
        },
        "accounting": {
            "incremental_spend_usd": 0,
            "terminal_credit_delta": 0,
            "acceptance_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
        "hard_nonclaims": [
            "CHECKPOINT_COMPLETION_IS_NOT_GLOBAL_OPEN_ENDED_MISSION_COMPLETION",
            "GLOBAL_OPEN_ENDED_MISSION_COMPLETE_REMAINS_NON_DERIVABLE",
            "ZERO_TERMINAL_CREDIT_UNTIL_EVERY_CONJUNCT_GENUINELY_CLOSES",
            "OPEN_CLAIM_STATES_ARE_UNSATISFIFIED_OBLIGATIONS_NOT_PROGRESS",
        ],
    }


def validate_emitted_manifest(doc: Mapping[str, Any], *, expected_epoch: str | None = None) -> dict[str, Any]:
    """Fail-closed structural validation of an emitted checkpoint manifest."""
    errors: list[str] = []
    if not isinstance(doc, Mapping):
        _fail("MANIFEST_NOT_OBJECT")
    if doc.get("schema") != SCHEMA:
        errors.append("SCHEMA_DRIFT")
    epoch = doc.get("epoch")
    if not isinstance(epoch, str) or not epoch.startswith(EPOCH_PREFIX + "__"):
        errors.append("EPOCH_MALFORMED")
    if expected_epoch is not None and epoch != expected_epoch:
        errors.append("EPOCH_MISMATCH")

    claims = doc.get("claims")
    if not isinstance(claims, list) or not claims:
        _fail("CLAIMS_INVALID")

    basis = doc.get("recomputed_obligation_basis") or {}
    basis_ids = basis.get("basis_family_ids")
    if not isinstance(basis_ids, list) or not basis_ids:
        errors.append("BASIS_IDS_INVALID")
        basis_ids = []

    seen_ids: set[str] = set()
    seen_families: set[str] = set()
    proofed_families = {
        p.get("family_id")
        for p in (basis.get("alias_equivalence_proofs") or [])
        if isinstance(p, Mapping)
    }
    for index, row in enumerate(claims):
        if not isinstance(row, Mapping):
            errors.append(f"CLAIM_ROW_NOT_OBJECT:{index}")
            continue
        claim = row.get("claim")
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_CORE_MISSING:{index}")
            continue
        if claim.get("claim_kind") != CLAIM_KIND:
            errors.append(f"CLAIM_KIND_NOT_CHECKPOINT_ACCEPTANCE:{index}")
        if claim.get("claim_id") != compute_claim_id(claim):
            errors.append(f"CLAIM_ID_MISMATCH:{index}")
        if claim.get("epoch") != epoch:
            errors.append(f"CLAIM_EPOCH_MISMATCH:{index}")
        if int(claim.get("terminal_credit_delta") or 0) != 0:
            errors.append(f"NONZERO_CREDIT_FORBIDDEN:{index}")
        cid = claim.get("claim_id")
        fid = row.get("family_id")
        if cid in seen_ids and fid not in proofed_families:
            errors.append(f"ALIAS_WITHOUT_EQUIVALENCE_PROOF:{index}")
        seen_ids.add(str(cid))
        if fid in seen_families:
            errors.append(f"DUPLICATE_FAMILY_CLAIM:{index}")
        seen_families.add(str(fid))
        verdict = validate_claim(claim, current_mission_blob_sha=claim.get("mission_blob_sha") or "")
        if verdict.get("pass") is not True:
            # mission-binding currency is checked separately against live bytes
            core_errors = [e for e in verdict.get("errors", []) if e != "MISSION_BINDING_STALE"]
            if core_errors:
                errors.append(f"CLAIM_CORE_INVALID:{index}:{core_errors}")

    if basis_ids and sorted(seen_families) != sorted(str(x) for x in basis_ids):
        errors.append("CLAIM_SET_NOT_BIJECTIVE_WITH_BASIS")

    theorem = doc.get("scope_completeness_theorem") or {}
    if theorem.get("statement") != SCOPE_COMPLETENESS_THEOREM:
        errors.append("SCOPE_COMPLETENESS_THEOREM_DRIFT")
    if theorem.get("proved") is not True:
        errors.append("SCOPE_COMPLETENESS_NOT_PROVED")

    aggregate = doc.get("aggregate") or {}
    satisfied = [row for row in claims if isinstance(row, Mapping) and row.get("satisfied") is True]
    recomputed_complete = bool(
        aggregate.get("scope_complete") is True
        and aggregate.get("all_required_claims_sound") is True
        and len(satisfied) == len(claims)
        and aggregate.get("reducer_closure_achieved") is True
    )
    if aggregate.get("checkpoint_complete") != recomputed_complete:
        errors.append("AGGREGATION_RULE_INCONSISTENT")
    if aggregate.get("checkpoint_complete") is True and len(satisfied) != len(claims):
        errors.append("CHECKPOINT_COMPLETE_WITH_OPEN_CLAIMS")
    if aggregate.get("global_mission_completion_derivable") is not False:
        errors.append("GLOBAL_MISSION_COMPLETION_MUST_BE_NON_DERIVABLE")
    if aggregate.get("global_open_ended_mission_complete") is not False:
        errors.append("GLOBAL_OPEN_ENDED_MISSION_COMPLETE_MUST_BE_FALSE")

    accounting = doc.get("accounting") or {}
    for key in ("incremental_spend_usd", "terminal_credit_delta", "acceptance_credit_delta", "ownership_credit_delta"):
        if accounting.get(key, 1) != 0:
            errors.append(f"NONZERO_ACCOUNTING:{key}")

    return {
        "pass": not errors,
        "status": "PASS__CLAIM_SCOPED_CHECKPOINT_MANIFEST_VALID" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "required_claim_count": len(claims),
        "satisfied_claim_count": len(satisfied),
        "checkpoint_complete": aggregate.get("checkpoint_complete") is True,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }


def verify_current(doc: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify the emitted manifest against live current sources under one epoch."""
    aggregate = compile_checkpoint_aggregate()
    if doc is None:
        emitted_path = ROOT / EMITTED_MANIFEST_REL
        _require(emitted_path.is_file(), "EMITTED_MANIFEST_MISSING")
        doc = _load_json(emitted_path)
    structural = validate_emitted_manifest(doc, expected_epoch=aggregate["epoch"])
    errors = list(structural["errors"])
    live_ids = {row["family_id"]: row["claim"]["claim_id"] for row in aggregate["claims"]}
    emitted_ids = {row.get("family_id"): (row.get("claim") or {}).get("claim_id") for row in doc.get("claims", [])}
    if live_ids != emitted_ids:
        errors.append("EMITTED_CLAIM_SET_DRIFTED_FROM_CURRENT_BASIS")
    if doc.get("epoch") != aggregate["epoch"]:
        errors.append("EMITTED_EPOCH_DRIFTED_FROM_CURRENT_SOURCES")
    return {
        "pass": not errors,
        "status": "PASS__EMITTED_MANIFEST_CURRENT_AND_SCOPE_COMPLETE" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "epoch": aggregate["epoch"],
        "required_claim_count": structural["required_claim_count"],
        "satisfied_claim_count": structural["satisfied_claim_count"],
        "checkpoint_complete": aggregate["aggregate"]["checkpoint_complete"],
        "open_claim_count": aggregate["aggregate"]["open_claim_count"],
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim-scoped Opus checkpoint aggregator (#3743)")
    parser.add_argument("command", choices=["evaluate", "emit", "verify"])
    args = parser.parse_args()

    if args.command == "evaluate":
        result = compile_checkpoint_aggregate()
        summary = {
            "schema": SCHEMA,
            "epoch": result["epoch"],
            "required_claim_count": result["aggregate"]["required_claim_count"],
            "satisfied_claim_count": result["aggregate"]["satisfied_claim_count"],
            "open_claim_count": result["aggregate"]["open_claim_count"],
            "checkpoint_complete": result["aggregate"]["checkpoint_complete"],
            "global_mission_completion_derivable": False,
            "terminal_credit_delta": 0,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    if args.command == "emit":
        result = compile_checkpoint_aggregate()
        structural = validate_emitted_manifest(result, expected_epoch=result["epoch"])
        if structural["pass"] is not True:
            print(json.dumps(structural, indent=2, sort_keys=True))
            return 1
        emitted_path = ROOT / EMITTED_MANIFEST_REL
        emitted_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "status": "EMITTED__SCOPE_COMPLETE",
                    "path": EMITTED_MANIFEST_REL,
                    "git_blob_sha": _git_blob_sha(emitted_path),
                    "epoch": result["epoch"],
                    "required_claim_count": result["aggregate"]["required_claim_count"],
                    "satisfied_claim_count": result["aggregate"]["satisfied_claim_count"],
                    "checkpoint_complete": result["aggregate"]["checkpoint_complete"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    result = verify_current()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
