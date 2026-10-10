"""Batch freezer for the twelve professional semantic-totality property claims.

This module removes repetitive claim construction only. It does NOT prove
semantic property truth and never transports root certificates across claim IDs.

For each current professional semantic leaf it:
- reuses the independently verified whole-leaf scope batch,
- binds the exact manifest semantic acceptance and bounded witness receipt,
- freezes one PROPERTY_CERTIFICATE claim under the current mission pointer bytes,
- validates the claim with the canonical coverage claim-scope guard,
- leaves carrier factorization and CC_R1/CC_R2/CC_R3 proof status OPEN.

The canonical root registry remains single-active-claim. This pack is therefore
a queue of separately frozen proof obligations, not multi-claim authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import coverage_claim_scope_guard_v1 as claim_guard
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as scope_batch

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_V2"
EPOCH = "PROFESSIONAL_SEMANTIC_TOTALITY_BATCH_20261010_V2"
AUTHORITY_ID = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_COVERAGE_AUTHORITY_V2"
SEMANTIC_SUFFIX = "::SEMANTIC"
RESIDUAL = "PROVE_TOTALITY_OVER_ALL_ADMISSIBLE_LEAF_INPUTS_OR_BIND_INDEPENDENT_CERTIFIED_COMPLETE_UNION"
EXPECTED_SEMANTIC_COUNT = 12

PINS = {
    "manifest": (
        "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json",
        "a7cad32c9fd969ff2c3857bb924c7bd746237ec2",
    ),
    "residual_ledger": (
        "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json",
        "ae5503829ad340cccef287f37ff70e4ab9288d33",
    ),
    "scope_batch_runtime": (
        "canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py",
        "82ab66c7852fc327821b23ff80dd46de3b81525c",
    ),
    "scope_batch_verify": (
        "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
        "4c2d40a262f18f34bb35f94b59660d60972d45ef",
    ),
    "claim_guard": (
        "canonical/runtime/coverage_claim_scope_guard_v1.py",
        "d1de61aa9bc00a184772a50f7ec9d5ee2853d747",
    ),
    "semantic_reduction": (
        "canonical/governance/PROFESSIONAL_SEMANTIC_TOTALITY_REUSE_REDUCTION_20261010_V1.json",
        "ab7e1c6ac1aad3b6bd3f32dfc959cefc903cbb6d",
    ),
}
MISSION_PATH = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return value


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_claim_count": 0,
        "unique_claim_id_count": 0,
        "root_proved_claim_count": 0,
        "property_truth_claim_count": 0,
        "single_active_claim_policy_preserved": True,
        "cross_claim_root_transport_authorized": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _manifest_semantic_leaves(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for root in manifest.get("roots") or []:
        if not isinstance(root, Mapping):
            continue
        leaf = root.get("semantic_leaf")
        if not isinstance(leaf, Mapping):
            continue
        leaf_id = leaf.get("id")
        if isinstance(leaf_id, str) and leaf_id.endswith(SEMANTIC_SUFFIX):
            if leaf_id in out:
                raise ValueError("DUPLICATE_MANIFEST_SEMANTIC_LEAF:" + leaf_id)
            out[leaf_id] = leaf
    return out


def _ledger_semantic_rows(ledger: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in ledger.get("leaves") or []:
        if not isinstance(row, Mapping):
            continue
        leaf_id = row.get("leaf_id")
        if isinstance(leaf_id, str) and leaf_id.endswith(SEMANTIC_SUFFIX):
            if leaf_id in out:
                raise ValueError("DUPLICATE_LEDGER_SEMANTIC_LEAF:" + leaf_id)
            out[leaf_id] = row
    return out


def project_documents(
    manifest: Mapping[str, Any],
    ledger: Mapping[str, Any],
    batch_out: Mapping[str, Any],
    *,
    current_mission_blob_sha: str,
) -> dict[str, Any]:
    try:
        manifest_leaves = _manifest_semantic_leaves(manifest)
        ledger_rows = _ledger_semantic_rows(ledger)
    except ValueError as exc:
        return _fail(str(exc))

    if len(manifest_leaves) != EXPECTED_SEMANTIC_COUNT:
        return _fail("MANIFEST_SEMANTIC_LEAF_COUNT_INVALID", observed=len(manifest_leaves))
    if set(ledger_rows) != set(manifest_leaves):
        return _fail(
            "LEDGER_MANIFEST_SEMANTIC_LEAF_SET_MISMATCH",
            manifest_leaf_ids=sorted(manifest_leaves),
            ledger_leaf_ids=sorted(ledger_rows),
        )

    if batch_out.get("pass") is not True:
        return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_PASS")
    if batch_out.get("scope_complete_count") != 24 or batch_out.get("unique_claim_id_count") != 24:
        return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")

    scope_rows = {
        row.get("leaf_id"): row
        for row in batch_out.get("rows") or []
        if isinstance(row, Mapping) and isinstance(row.get("leaf_id"), str)
    }
    if len(scope_rows) != 24:
        return _fail("WHOLE_LEAF_SCOPE_BATCH_ROWS_INVALID", observed=len(scope_rows))

    claims: list[dict[str, Any]] = []
    for leaf_id in sorted(manifest_leaves):
        manifest_leaf = manifest_leaves[leaf_id]
        ledger_row = ledger_rows[leaf_id]
        scope_row = scope_rows.get(leaf_id)
        if not isinstance(scope_row, Mapping):
            return _fail("SEMANTIC_SCOPE_ROW_MISSING", leaf_id=leaf_id)
        if (
            scope_row.get("whole_leaf_domain_equivalence_proved") is not True
            or scope_row.get("whole_leaf_scope_complete") is not True
            or scope_row.get("leaf_property_truth_authority") is not False
        ):
            return _fail("SEMANTIC_SCOPE_ROW_NOT_PROPERTY_READY", leaf_id=leaf_id)

        if ledger_row.get("residual") != RESIDUAL:
            return _fail("SEMANTIC_RESIDUAL_DRIFT", leaf_id=leaf_id)
        witnesses = ledger_row.get("bounded_witnesses")
        if not isinstance(witnesses, list) or not witnesses:
            return _fail("SEMANTIC_BOUNDED_WITNESS_REQUIRED", leaf_id=leaf_id)
        normalized_witnesses = []
        for witness in witnesses:
            if not isinstance(witness, Mapping):
                return _fail("SEMANTIC_BOUNDED_WITNESS_INVALID", leaf_id=leaf_id)
            if witness.get("global_leaf_closure") is not False:
                return _fail("SEMANTIC_WITNESS_GLOBAL_PROMOTION_FORBIDDEN", leaf_id=leaf_id)
            receipt = witness.get("source_receipt")
            if not isinstance(receipt, Mapping):
                return _fail("SEMANTIC_WITNESS_RECEIPT_REQUIRED", leaf_id=leaf_id)
            if not isinstance(receipt.get("path"), str) or not isinstance(receipt.get("git_blob_sha"), str):
                return _fail("SEMANTIC_WITNESS_RECEIPT_BINDING_INVALID", leaf_id=leaf_id)
            normalized_witnesses.append({
                "scope_id": witness.get("scope_id"),
                "root_id": witness.get("root_id"),
                "claim_kind": witness.get("claim_kind"),
                "source_receipt": {
                    "path": receipt.get("path"),
                    "git_blob_sha": receipt.get("git_blob_sha"),
                },
                "global_leaf_closure": False,
            })

        acceptance = manifest_leaf.get("acceptance")
        obligation = manifest_leaf.get("obligation")
        if not isinstance(acceptance, str) or not acceptance:
            return _fail("SEMANTIC_MANIFEST_ACCEPTANCE_MISSING", leaf_id=leaf_id)
        if not isinstance(obligation, str) or not obligation:
            return _fail("SEMANTIC_MANIFEST_OBLIGATION_MISSING", leaf_id=leaf_id)

        scope_sha = scope_row.get("scope_definition_sha256")
        if not isinstance(scope_sha, str) or len(scope_sha) != 64:
            return _fail("SEMANTIC_SCOPE_SHA256_INVALID", leaf_id=leaf_id)

        target_predicate = {
            "leaf_id": leaf_id,
            "obligation": obligation,
            "acceptance": acceptance,
            "quantification": "FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE",
        }
        semantics = {
            "semantics_id": leaf_id + "::PROPERTY_TRUTH_SEMANTICS_V1",
            "true_when": acceptance,
            "false_when": "EXISTS_ADMISSIBLE_INPUT_IN_WHOLE_LEAF_SCOPE_FOR_WHICH_THE_ACCEPTANCE_PROPERTY_FAILS",
            "unknown_when": "CLAIM_SCOPED_TOTALITY_OR_INDEPENDENT_CERTIFIED_COMPLETE_UNION_NOT_YET_PROVED",
            "bounded_witnesses": normalized_witnesses,
            "bounded_witnesses_are_totality_authority": False,
            "required_totality_route": (
                "MISSION_SUFFICIENT_SEMANTIC_CARRIER__COVERAGE_COMPLETENESS_FOUR_ROOT_THEOREM__"
                "UNIVERSAL_SCOPE_TOTALITY_OR_INDEPENDENT_CERTIFIED_COMPLETE_UNION"
            ),
        }

        claim = {
            "claim_kind": "PROPERTY_CERTIFICATE",
            "mission_blob_sha": current_mission_blob_sha,
            "scope_sha256": scope_sha,
            "target_predicate_sha256": _digest(target_predicate),
            "semantics_sha256": _digest(semantics),
            "epoch": EPOCH,
            "authority_id": AUTHORITY_ID,
        }
        claim["claim_id"] = claim_guard.compute_claim_id(claim)
        claim["terminal_credit_delta"] = 0
        verdict = claim_guard.validate_claim(
            claim,
            current_mission_blob_sha=current_mission_blob_sha,
        )
        if verdict.get("pass") is not True:
            return _fail("SEMANTIC_FROZEN_CLAIM_INVALID", leaf_id=leaf_id, verdict=verdict)

        claims.append({
            "leaf_id": leaf_id,
            "root_id": leaf_id[len("PQ::"):-len(SEMANTIC_SUFFIX)],
            "whole_leaf_scope_claim_id": scope_row.get("claim_id"),
            "scope_definition_sha256": scope_sha,
            "target_predicate": target_predicate,
            "semantics": semantics,
            "frozen_claim": claim,
            "claim_guard_pass": True,
            "mission_sufficient_carrier_factorization_proved": False,
            "cc_r1_reality_containment_proved": False,
            "cc_r2_mission_soundness_proved": False,
            "cc_r3_terminal_closure_proved": False,
            "r4_proof_closure": False,
            "semantic_property_truth_authority": False,
            "activation_authorized": False,
        })

    claim_ids = [row["frozen_claim"]["claim_id"] for row in claims]
    if len(claim_ids) != EXPECTED_SEMANTIC_COUNT or len(set(claim_ids)) != EXPECTED_SEMANTIC_COUNT:
        return _fail("SEMANTIC_FROZEN_CLAIM_IDS_NOT_UNIQUE", claim_ids=claim_ids)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__TWELVE_DISTINCT_CONTENT_ADDRESSED_SEMANTIC_TOTALITY_CLAIMS_FROZEN__"
            "CLAIM_SPECIFIC_ROOT_PROOFS_STILL_OPEN__ZERO_PROPERTY_TRUTH_CREDIT"
        ),
        "epoch": EPOCH,
        "authority_id": AUTHORITY_ID,
        "mission_blob_sha": current_mission_blob_sha,
        "semantic_claim_count": len(claims),
        "unique_claim_id_count": len(set(claim_ids)),
        "claim_id_set_sha256": _digest(sorted(claim_ids)),
        "root_proved_claim_count": 0,
        "property_truth_claim_count": 0,
        "single_active_claim_policy_preserved": True,
        "cross_claim_root_transport_authorized": False,
        "activation_policy": (
            "ACTIVATE_AT_MOST_ONE_FROZEN_CLAIM_IN_CANONICAL_ROOT_REGISTRY_AT_A_TIME__"
            "CLAIM_SPECIFIC_CC_R1_CC_R2_CC_R3_AND_R4_REQUIRED"
        ),
        "next": (
            "RANK_TWELVE_FROZEN_CLAIMS_BY_EXISTING_PROOF_REUSE__ACTIVATE_ONE__"
            "PROVE_CLAIM_SPECIFIC_CARRIER_FACTORIZATION_AND_CC_R1_CC_R2_CC_R3_R4__"
            "THEN_RUN_SEMANTIC_LEAF_PROPERTY_TRUTH_VERIFIER"
        ),
        "claims": claims,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT

    for key, (rel, expected) in PINS.items():
        path = root / rel
        if not path.is_file() or path.is_symlink():
            return _fail(key.upper() + "_MISSING")
        actual = _blob(path)
        if actual != expected:
            return _fail(key.upper() + "_BLOB_STALE", expected=expected, observed=actual)

    mission_path = root / MISSION_PATH
    if not mission_path.is_file() or mission_path.is_symlink():
        return _fail("CURRENT_MISSION_OBJECTIVE_MISSING")
    mission_blob = _blob(mission_path)

    try:
        manifest = _load(root / PINS["manifest"][0])
        ledger = _load(root / PINS["residual_ledger"][0])
    except Exception as exc:
        return _fail("BOUND_SOURCE_JSON_INVALID", detail=type(exc).__name__ + ":" + str(exc))

    # Content-address every bounded semantic witness receipt before using it in
    # frozen claim semantics.
    for row in _ledger_semantic_rows(ledger).values():
        for witness in row.get("bounded_witnesses") or []:
            if not isinstance(witness, Mapping):
                return _fail("SEMANTIC_BOUNDED_WITNESS_INVALID")
            ref = witness.get("source_receipt")
            if not isinstance(ref, Mapping):
                return _fail("SEMANTIC_WITNESS_RECEIPT_REQUIRED")
            rel = ref.get("path")
            expected = ref.get("git_blob_sha")
            if not isinstance(rel, str) or not rel.startswith("canonical/verification/"):
                return _fail("SEMANTIC_WITNESS_RECEIPT_PATH_INVALID", path=rel)
            p = root / rel
            if not p.is_file() or p.is_symlink():
                return _fail("SEMANTIC_WITNESS_RECEIPT_MISSING", path=rel)
            actual = _blob(p)
            if actual != expected:
                return _fail(
                    "SEMANTIC_WITNESS_RECEIPT_BLOB_STALE",
                    path=rel,
                    expected=expected,
                    observed=actual,
                )

    batch_out = scope_batch.verify(repo_root=root)
    return project_documents(
        manifest,
        ledger,
        batch_out,
        current_mission_blob_sha=mission_blob,
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
