"""Fail-closed admission gate for professional semantic leaf property truth.

The current professional semantic leaves are universal property claims over
their independently verified whole-leaf input domains. A proof that the runtime
can safely abstain, or that all *declared* defeaters have fail-closed handlers,
does not by itself prove that universal positive property.

This gate separates three statements that are easy to conflate:

1. safe terminal behavior: every run either positively certifies or safely
   abstains;
2. nonvacuity: at least one positive certification exists;
3. universal semantic property truth: every admissible input satisfies the
   exact semantic leaf target predicate.

Only (3), or a stronger proof that entails it, can authorize semantic leaf
property truth. Safe abstention remains valuable behavior but has zero positive
property-truth credit unless the exact target predicate explicitly accepts it
or the abstaining cases are proved outside the frozen claim scope.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_PROPERTY_TRUTH_ADMISSION_V1"
PACK_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_V2"
PACK_PATH = "canonical/governance/PROFESSIONAL_SEMANTIC_TOTALITY_FROZEN_CLAIM_PACK_20261010_V2.json"
PACK_BLOB = "f16aab3760d4f5958da986782632f3cb2bbd2646"
MISSION_PATH = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"

ROOT_PROOF_FIELDS = (
    "mission_sufficient_carrier_factorization_proved",
    "cc_r1_reality_containment_proved",
    "cc_r2_mission_soundness_proved",
    "cc_r3_terminal_closure_proved",
    "r4_proof_closure",
)
ACCEPTANCE_ATOM_FIELDS = (
    "claim_semantics_grounding_totality_proved",
    "scope_uncertainty_resolution_totality_proved",
    "root_relevant_defeater_totality_proved",
    "typed_evidence_totality_proved",
)
ALLOWED_PROOF_MODES = {
    "CLAIM_SCOPED_COVERAGE_ROOTS",
    "INDEPENDENT_DIRECT_UNIVERSAL_PROOF",
}


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "leaf_property_truth_admissible": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _claim_rows(pack: Mapping[str, Any]) -> dict[str, Mapping[str, Any]] | None:
    if pack.get("schema") != PACK_SCHEMA or pack.get("pass") is not True:
        return None
    if pack.get("semantic_claim_count") != 12 or pack.get("unique_claim_id_count") != 12:
        return None
    if pack.get("root_proved_claim_count") != 0 or pack.get("property_truth_claim_count") != 0:
        return None
    rows = pack.get("claims")
    if not isinstance(rows, list) or len(rows) != 12:
        return None
    out: dict[str, Mapping[str, Any]] = {}
    claim_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return None
        leaf = row.get("leaf_id")
        claim = row.get("frozen_claim")
        if not isinstance(leaf, str) or not isinstance(claim, Mapping):
            return None
        cid = claim.get("claim_id")
        if not isinstance(cid, str) or len(cid) != 64 or leaf in out or cid in claim_ids:
            return None
        out[leaf] = row
        claim_ids.add(cid)
    return out


def evaluate_candidate(
    pack: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    current_mission_blob_sha: str,
) -> dict[str, Any]:
    rows = _claim_rows(pack)
    if rows is None:
        return _fail("SEMANTIC_CLAIM_PACK_INVALID")

    if pack.get("mission_blob_sha") != current_mission_blob_sha:
        return _fail(
            "SEMANTIC_CLAIM_PACK_MISSION_STALE",
            pack_mission_blob_sha=pack.get("mission_blob_sha"),
            current_mission_blob_sha=current_mission_blob_sha,
        )

    if not isinstance(candidate, Mapping):
        return _fail("CANDIDATE_NOT_OBJECT")

    leaf_id = candidate.get("leaf_id")
    if not isinstance(leaf_id, str) or leaf_id not in rows:
        return _fail("LEAF_NOT_IN_CURRENT_SEMANTIC_CLAIM_PACK", leaf_id=leaf_id)

    row = rows[leaf_id]
    frozen_claim = row["frozen_claim"]
    current_claim_id = frozen_claim["claim_id"]

    if candidate.get("semantic_totality_claim_id") != current_claim_id:
        return _fail(
            "SEMANTIC_TOTALITY_CLAIM_ID_MISMATCH",
            leaf_id=leaf_id,
            expected_claim_id=current_claim_id,
            observed_claim_id=candidate.get("semantic_totality_claim_id"),
        )

    target = row.get("target_predicate")
    semantics = row.get("semantics")
    if not isinstance(target, Mapping) or not isinstance(semantics, Mapping):
        return _fail("CURRENT_SEMANTIC_CLAIM_MATERIAL_INVALID", leaf_id=leaf_id)

    if target.get("quantification") != "FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE":
        return _fail("TARGET_NOT_UNIVERSAL", leaf_id=leaf_id)

    exact_acceptance = target.get("acceptance")
    if not isinstance(exact_acceptance, str) or not exact_acceptance:
        return _fail("TARGET_ACCEPTANCE_INVALID", leaf_id=leaf_id)
    if candidate.get("leaf_acceptance") != exact_acceptance:
        return _fail("LEAF_ACCEPTANCE_MISMATCH", leaf_id=leaf_id)

    if candidate.get("whole_leaf_scope_complete") is not True:
        return _fail("WHOLE_LEAF_SCOPE_COMPLETENESS_REQUIRED", leaf_id=leaf_id)

    mode = candidate.get("proof_mode")
    if mode not in ALLOWED_PROOF_MODES:
        return _fail("PROOF_MODE_INVALID", leaf_id=leaf_id, proof_mode=mode)

    atoms = candidate.get("acceptance_atom_proofs")
    if not isinstance(atoms, Mapping):
        return _fail("ACCEPTANCE_ATOM_PROOFS_REQUIRED", leaf_id=leaf_id)
    missing_atoms = [field for field in ACCEPTANCE_ATOM_FIELDS if atoms.get(field) is not True]
    if missing_atoms:
        return _fail(
            "SEMANTIC_ACCEPTANCE_TOTALITY_NOT_PROVED",
            leaf_id=leaf_id,
            missing_acceptance_atoms=missing_atoms,
        )

    if mode == "CLAIM_SCOPED_COVERAGE_ROOTS":
        roots = candidate.get("claim_scoped_root_proofs")
        if not isinstance(roots, Mapping):
            return _fail("CLAIM_SCOPED_ROOT_PROOFS_REQUIRED", leaf_id=leaf_id)
        missing_roots = [field for field in ROOT_PROOF_FIELDS if roots.get(field) is not True]
        if missing_roots:
            return _fail(
                "CLAIM_SCOPED_ROOT_CLOSURE_INCOMPLETE",
                leaf_id=leaf_id,
                missing_root_proofs=missing_roots,
            )
    else:
        direct = candidate.get("direct_universal_proof")
        if not isinstance(direct, Mapping):
            return _fail("DIRECT_UNIVERSAL_PROOF_REQUIRED", leaf_id=leaf_id)
        if (
            direct.get("all_admissible_inputs_satisfy_exact_target_predicate") is not True
            or direct.get("independently_verified") is not True
            or direct.get("scope_relation") != "EXACT"
        ):
            return _fail("DIRECT_UNIVERSAL_PROOF_INCOMPLETE", leaf_id=leaf_id)

    disposition = candidate.get("terminal_disposition")
    if not isinstance(disposition, Mapping):
        return _fail("TERMINAL_DISPOSITION_PROOF_REQUIRED", leaf_id=leaf_id)

    abstention_reachable = disposition.get("justified_abstention_reachable") is True
    abstention_satisfies = disposition.get("abstention_satisfies_exact_target_predicate") is True
    abstention_outside_scope = disposition.get("abstention_inputs_outside_claim_scope_proved") is True
    positive_totality = disposition.get("positive_issuance_totality_proved") is True

    # For the current claims the exact target is a universal positive semantic
    # predicate. If an in-scope run can terminate in abstention and abstention
    # does not itself satisfy that exact predicate, safe terminal closure is
    # weaker than property truth.
    if abstention_reachable and not abstention_satisfies and not abstention_outside_scope:
        return _fail(
            "SAFE_ABSTENTION_DOES_NOT_IMPLY_UNIVERSAL_POSITIVE_PROPERTY",
            leaf_id=leaf_id,
        )

    if not positive_totality and not (abstention_satisfies or abstention_outside_scope):
        return _fail(
            "UNIVERSAL_POSITIVE_ISSUANCE_TOTALITY_REQUIRED",
            leaf_id=leaf_id,
        )

    nonvacuity = candidate.get("nonvacuity")
    if not isinstance(nonvacuity, Mapping):
        return _fail("NONVACUITY_PROOF_REQUIRED", leaf_id=leaf_id)
    count = nonvacuity.get("independently_verified_positive_witness_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return _fail("POSITIVE_NONVACUITY_WITNESS_REQUIRED", leaf_id=leaf_id)

    if candidate.get("independent_verification_pass") is not True:
        return _fail("INDEPENDENT_VERIFICATION_REQUIRED", leaf_id=leaf_id)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CURRENT_CLAIM_BOUND_UNIVERSAL_SEMANTIC_PROPERTY_TRUTH_ADMISSIBLE",
        "leaf_id": leaf_id,
        "semantic_totality_claim_id": current_claim_id,
        "leaf_acceptance": exact_acceptance,
        "proof_mode": mode,
        "acceptance_atom_totality_proved": True,
        "claim_scoped_root_closure_proved": mode == "CLAIM_SCOPED_COVERAGE_ROOTS",
        "direct_universal_proof": mode == "INDEPENDENT_DIRECT_UNIVERSAL_PROOF",
        "positive_issuance_totality_proved": positive_totality,
        "safe_abstention_substituted_for_positive_property": False,
        "nonvacuous_positive_witness_count": count,
        "leaf_property_truth_admissible": True,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def verify_candidate(
    candidate: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pack_path = root / PACK_PATH
    mission_path = root / MISSION_PATH
    if not pack_path.is_file() or pack_path.is_symlink():
        return _fail("SEMANTIC_CLAIM_PACK_MISSING")
    if _blob(pack_path) != PACK_BLOB:
        return _fail(
            "SEMANTIC_CLAIM_PACK_BLOB_STALE",
            expected_blob=PACK_BLOB,
            observed_blob=_blob(pack_path),
        )
    if not mission_path.is_file() or mission_path.is_symlink():
        return _fail("CURRENT_MISSION_POINTER_MISSING")
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("SEMANTIC_CLAIM_PACK_JSON_INVALID")
    return evaluate_candidate(
        pack,
        candidate,
        current_mission_blob_sha=_blob(mission_path),
    )
