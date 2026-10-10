"""Reinstantiate R12 semantic clause C1 on the current stable V3 claim.

This verifier does not transport the historical C1 certificate. It creates a
fresh claim binding to the already independently replayed exact V4 12-of-12
same-subject composition proof.

C1 is proved only at the root-binding -> same-subject composition boundary.
Internal root semantic completeness, C8 nonvacuity, unknown-material-defeater
totality, CC_R3, leaf property truth, and terminal authority remain open.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_STABLE_C1_V1"
LEAF_ID = "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAUSE_ID = "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION"
CURRENT_CLAIM_ID = "11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
OLD_CLAIM_ID = "05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"

INPUT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INPUT_20261010_V1.json"
INPUT_BLOB = "8063d124d6fbd239814380ef4fbc710350a1dea8"
GATE_PATH = "canonical/runtime/professional_quality_same_subject_composition_gate_v4.py"
GATE_BLOB = "e1cc6200286c7b400fc7be70ef0789b85af7fe61"
REPLAY_PATH = "canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json"
REPLAY_BLOB = "4ee02c41acf64b1f47ebadec55b6bb5453d676ba"

EXPECTED_SUBJECT = (
    "DECLARED_SYSTEM",
    "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6",
    "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e",
)


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


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
    row = next(
        (
            x for x in (out.get("claims") or [])
            if isinstance(x, Mapping) and x.get("leaf_id") == LEAF_ID
        ),
        None,
    )
    return dict(row) if isinstance(row, Mapping) else None


def evaluate(
    *,
    r12_claim: Mapping[str, Any],
    composition_input: Mapping[str, Any],
    composition_replay: Mapping[str, Any],
    gate_blob: str,
) -> dict[str, Any]:
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

    if not isinstance(composition_input, Mapping):
        return _fail("COMPOSITION_INPUT_NOT_MAPPING")
    subject = (
        composition_input.get("subject_kind"),
        composition_input.get("subject_id"),
        composition_input.get("subject_sha256"),
    )
    if subject != EXPECTED_SUBJECT:
        return _fail("COMPOSITION_SUBJECT_DRIFT", observed_subject=subject)
    rows = composition_input.get("root_subject_bindings")
    if not isinstance(rows, list) or len(rows) != 12:
        return _fail("COMPOSITION_INPUT_ROOT_COUNT_DRIFT")
    ids = [x.get("root_id") for x in rows if isinstance(x, Mapping)]
    if len(ids) != 12 or len(set(ids)) != 12:
        return _fail("COMPOSITION_INPUT_ROOT_IDENTITY_INVALID")

    if gate_blob != GATE_BLOB:
        return _fail("COMPOSITION_GATE_BLOB_DRIFT", observed=gate_blob)

    if not isinstance(composition_replay, Mapping):
        return _fail("COMPOSITION_REPLAY_NOT_MAPPING")
    if composition_replay.get("git_blob_sha") is not None:
        return _fail("COMPOSITION_REPLAY_WRAPPER_INVALID")
    if not str(composition_replay.get("status") or "").startswith(
        "PASS__INDEPENDENT_SPRITE_EXACT_V4_12_OF_12"
    ):
        return _fail("COMPOSITION_REPLAY_NOT_PASS")
    exact = composition_replay.get("exact_blobs") or {}
    if exact.get("composition_input") != INPUT_BLOB:
        return _fail("REPLAY_INPUT_BLOB_MISMATCH")
    if exact.get("composition_gate_v4") != GATE_BLOB:
        return _fail("REPLAY_GATE_BLOB_MISMATCH")
    replay = composition_replay.get("replay") or {}
    if replay.get("exact_root_binding_count") != 12:
        return _fail("REPLAY_ROOT_COUNT_MISMATCH")
    if replay.get("independent_adversarial_probes_passed") != 3:
        return _fail("REPLAY_ADVERSARIAL_PROBE_COUNT_MISMATCH")
    if replay.get("composition_result") != (
        "PASS__INDEPENDENT_EXACT_V4_12_OF_12_SAME_SUBJECT_COMPOSITION_REPLAY"
    ):
        return _fail("REPLAY_COMPOSITION_RESULT_MISMATCH")
    if composition_replay.get("composition_admissible") is not True:
        return _fail("REPLAY_COMPOSITION_NOT_ADMISSIBLE")
    if composition_replay.get("verified_root_subject_binding_count") != 12:
        return _fail("REPLAY_VERIFIED_ROOT_COUNT_MISMATCH")
    composed = composition_replay.get("composed_subject") or {}
    if (
        composed.get("subject_kind"),
        composed.get("subject_id"),
        composed.get("subject_sha256"),
    ) != EXPECTED_SUBJECT:
        return _fail("REPLAY_COMPOSED_SUBJECT_DRIFT")
    for field in (
        "semantic_truth_authority",
        "execution_authority",
        "quality_authority",
        "acceptance_authority",
        "promotion_authority",
        "terminal_authority",
    ):
        if composition_replay.get(field) is not False:
            return _fail("REPLAY_AUTHORITY_OVERCLAIM:" + field)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__STABLE_R12_C1_FRESH_CLAIM_BINDING_TO_INDEPENDENT_EXACT_V4_"
            "ASSUMPTION_GUARANTEE_COMPOSITION__ZERO_PROPERTY_CREDIT"
        ),
        "leaf_id": LEAF_ID,
        "clause_id": CLAUSE_ID,
        "claim_id": CURRENT_CLAIM_ID,
        "historical_claim_id_not_transported": OLD_CLAIM_ID,
        "proof_scope": (
            "EXACT_CURRENT_R12_SEMANTIC_CLAIM__ROOT_BINDING_TO_SAME_SUBJECT_"
            "COMPOSITION_BOUNDARY_ONLY"
        ),
        "proof_reuse": {
            "composition_input_git_blob_sha": INPUT_BLOB,
            "composition_gate_v4_git_blob_sha": GATE_BLOB,
            "independent_replay_git_blob_sha": REPLAY_BLOB,
            "fresh_claim_binding": True,
            "cross_claim_certificate_transport": False,
        },
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

    refs = (
        (INPUT_PATH, INPUT_BLOB, "COMPOSITION_INPUT"),
        (GATE_PATH, GATE_BLOB, "COMPOSITION_GATE"),
        (REPLAY_PATH, REPLAY_BLOB, "COMPOSITION_REPLAY"),
    )
    docs: dict[str, Any] = {}
    gate_blob = ""
    for rel, expected, label in refs:
        path = root / rel
        if not path.is_file() or path.is_symlink():
            return _fail(label + "_MISSING")
        actual = _blob(path)
        if actual != expected:
            return _fail(label + "_BLOB_STALE", expected=expected, observed=actual)
        if label == "COMPOSITION_GATE":
            gate_blob = actual
        else:
            try:
                docs[label] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return _fail(label + "_JSON_INVALID")

    return evaluate(
        r12_claim=r12,
        composition_input=docs["COMPOSITION_INPUT"],
        composition_replay=docs["COMPOSITION_REPLAY"],
        gate_blob=gate_blob,
    )


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
