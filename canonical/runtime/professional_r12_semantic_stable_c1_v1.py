"""Reinstantiate R12 semantic clause C1 on the current stable V3 claim.

C1 is proved only at the exact root-binding -> same-subject composition
boundary. This does not prove semantic completeness inside any root, C8
nonvacuity, unknown-material-defeater totality, CC_R3, or leaf property truth.

The proof is claim-specific. The historical C1 receipt for an older semantic
claim is not transported.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_quality_same_subject_composition_gate_v4 as gate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_STABLE_C1_V1"
LEAF_ID = "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAUSE_ID = "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION"
CURRENT_CLAIM_ID = "11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
OLD_CLAIM_ID = "05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
INPUT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INPUT_20261010_V1.json"
EXPECTED_INPUT_BLOB = "8063d124d6fbd239814380ef4fbc710350a1dea8"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "leaf_id": LEAF_ID,
        "clause_id": CLAUSE_ID,
        "claim_id": None,
        "c1_assumption_guarantee_composition_proved": False,
        "c8_nonvacuity_proved": False,
        "stronger_material_defeater_totality_proved": False,
        "cc_r3_terminal_closure_proved": False,
        "semantic_property_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "property_truth_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _current_r12_claim(root: Path) -> dict[str, Any] | None:
    out = pack_v3.verify(repo_root=root)
    if out.get("pass") is not True:
        return None
    rows = out.get("claims") or []
    row = next(
        (
            x for x in rows
            if isinstance(x, Mapping) and x.get("leaf_id") == LEAF_ID
        ),
        None,
    )
    return dict(row) if isinstance(row, Mapping) else None


def evaluate(
    *,
    r12_claim: Mapping[str, Any],
    composition_payload: Mapping[str, Any],
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(r12_claim, Mapping):
        return _fail("R12_CLAIM_NOT_MAPPING")
    frozen = r12_claim.get("frozen_claim")
    if not isinstance(frozen, Mapping):
        return _fail("R12_FROZEN_CLAIM_MISSING")
    claim_id = frozen.get("claim_id")
    if claim_id != CURRENT_CLAIM_ID:
        return _fail("R12_STABLE_CLAIM_ID_DRIFT", observed_claim_id=claim_id)
    if r12_claim.get("leaf_id") != LEAF_ID:
        return _fail("R12_LEAF_ID_DRIFT")
    if frozen.get("mission_blob_sha") != pack_v3.EXPECTED_MISSION_AUTHORITY_BLOB:
        return _fail("R12_MISSION_BINDING_DRIFT")

    if not isinstance(composition_payload, Mapping):
        return _fail("COMPOSITION_PAYLOAD_NOT_MAPPING")

    subject = (
        composition_payload.get("subject_kind"),
        composition_payload.get("subject_id"),
        composition_payload.get("subject_sha256"),
    )
    expected_subject = (
        "DECLARED_SYSTEM",
        "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6",
        "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e",
    )
    if subject != expected_subject:
        return _fail("COMPOSITION_SUBJECT_DRIFT", observed_subject=subject)

    gate_out = gate.evaluate(
        {"root_subject_bindings": deepcopy(composition_payload.get("root_subject_bindings"))},
        repo_root=root,
    )
    if gate_out.get("pass") is not True:
        return _fail(
            "SAME_SUBJECT_COMPOSITION_GATE_REJECTED",
            gate_status=gate_out.get("status"),
            gate_reason=gate_out.get("reason"),
        )
    if gate_out.get("composition_admissible") is not True:
        return _fail("COMPOSITION_NOT_ADMISSIBLE")
    if gate_out.get("verified_root_subject_binding_count") != 12:
        return _fail(
            "ROOT_BINDING_COUNT_NOT_TWELVE",
            observed=gate_out.get("verified_root_subject_binding_count"),
        )
    composed = gate_out.get("composed_subject") or {}
    if (
        composed.get("subject_kind"),
        composed.get("subject_id"),
        composed.get("subject_sha256"),
    ) != expected_subject:
        return _fail("GATE_COMPOSED_SUBJECT_DRIFT", composed_subject=composed)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__STABLE_R12_C1_EXACT_ROOT_BINDING_TO_SAME_SUBJECT_"
            "ASSUMPTION_GUARANTEE_COMPOSITION__ZERO_PROPERTY_CREDIT"
        ),
        "leaf_id": LEAF_ID,
        "clause_id": CLAUSE_ID,
        "claim_id": CURRENT_CLAIM_ID,
        "historical_claim_id_not_transported": OLD_CLAIM_ID,
        "proof_scope": (
            "EXACT_FROZEN_R12_CLAIM__ROOT_BINDING_TO_SAME_SUBJECT_"
            "COMPOSITION_BOUNDARY_ONLY"
        ),
        "assumptions": [
            "CURRENT_V3_R12_SEMANTIC_CLAIM_IS_EXACT_AND_STABLE",
            "EXACTLY_TWELVE_CONTENT_ADDRESSED_ROOT_BINDINGS_ARE_PRESENT",
            "EVERY_ROOT_BINDING_HAS_INDEPENDENT_PASSING_SCOPE_MATCHED_VERIFICATION",
            "ALL_ROOT_BINDINGS_SHARE_THE_IDENTICAL_V7_DECLARED_SYSTEM_SUBJECT",
            "MISSING_STALE_DUPLICATE_OR_CROSS_SUBJECT_BINDINGS_FAIL_CLOSED",
        ],
        "guarantee": {
            "composition_admissible": True,
            "verified_root_subject_binding_count": 12,
            "composed_subject": dict(composed),
            "authority_widening": False,
        },
        "c1_assumption_guarantee_composition_proved": True,
        "c8_nonvacuity_proved": False,
        "stronger_material_defeater_totality_proved": False,
        "cc_r3_terminal_closure_proved": False,
        "semantic_property_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "property_truth_credit_delta": 0,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_INTERNAL_ROOT_SEMANTIC_COMPLETENESS",
            "NO_C8_NONVACUITY_CREDIT",
            "NO_UNKNOWN_MATERIAL_DEFEATER_COMPLETENESS",
            "NO_CC_R3_TERMINAL_CLOSURE",
            "NO_R12_SEMANTIC_PROPERTY_TRUTH",
            "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY",
        ],
    }


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    r12 = _current_r12_claim(root)
    if r12 is None:
        return _fail("CURRENT_STABLE_R12_CLAIM_RESOLUTION_FAILED")
    path = root / INPUT_PATH
    if not path.is_file() or path.is_symlink():
        return _fail("COMPOSITION_INPUT_MISSING")
    from hashlib import sha1
    raw = path.read_bytes()
    blob = sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if blob != EXPECTED_INPUT_BLOB:
        return _fail(
            "COMPOSITION_INPUT_BLOB_STALE",
            expected=EXPECTED_INPUT_BLOB,
            observed=blob,
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return _fail("COMPOSITION_INPUT_JSON_INVALID")
    return evaluate(r12_claim=r12, composition_payload=payload, repo_root=root)


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
