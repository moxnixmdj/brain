"""Independent verifier for bounded CCoB/CCyB/TLAC context selection V1.

The producer uses regcap_context_signature_v1. This verifier does not import it.
It independently:
- binds the unique exact phrase "loss-absorbing cushion";
- extracts the containing sentence;
- tries the three bounded source-aligned context proof kinds;
- requires exactly one supported concept signature;
- re-authenticates the source-backed contrastive matrix;
- checks the producer selected the same concept only relative to the explicit
  CCoB/CCyB/TLAC task universe.

No global phrase identity or open-world ontology completeness is granted.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import source_aligned_regcap_context_proof_v1 as proof
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_SELECTION_VERIFY_V1"
CASE_SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_SELECTION_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_REGCAP_CONTEXT_SELECTION_RESULT_V1"
PHRASE = "loss-absorbing cushion"
CANDIDATES = (regcap.CCOB, regcap.CCYB, regcap.TLAC)


def _sha(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    return sha256(raw).hexdigest()


def _sentence(text: str, pos: int) -> tuple[int, int, str]:
    left = max(text.rfind(".", 0, pos), text.rfind("!", 0, pos), text.rfind("?", 0, pos)) + 1
    ends = [x for x in (text.find(".", pos), text.find("!", pos), text.find("?", pos)) if x >= 0]
    right = (min(ends) + 1) if ends else len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    return left, right, text[left:right]


def _claim(kind: str, length: int) -> dict[str, Any]:
    return {"claim_id": "verify", "kind": kind, "start": 0, "end": length}


def _supported_concepts(sentence: str) -> list[dict[str, Any]]:
    specs = [
        (
            regcap.CCOB,
            proof.CCOB_KIND,
            {
                proof.ATOM_2_5,
                proof.ATOM_CET1,
                proof.ATOM_ABOVE_MIN,
            },
            "STRUCTURAL_SIGNATURE_CLASS",
            "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        ),
        (
            regcap.CCYB,
            proof.CCYB_KIND,
            {proof.ATOM_RELEASE},
            "FUNCTIONAL_SIGNATURE_CLASS",
            "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        ),
        (
            regcap.TLAC,
            proof.TLAC_KIND,
            {
                proof.ATOM_LOSS,
                proof.ATOM_RECAP,
                proof.ATOM_RESOLUTION,
                proof.ATOM_GSIB,
            },
            "FUNCTIONAL_SIGNATURE_CLASS",
            "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
        ),
    ]
    found = []
    for concept_id, kind, required_atoms, observation_id, outcome in specs:
        checked = proof.verify_proof(
            sentence,
            source_id="independent-verifier",
            claims=[_claim(kind, len(sentence))],
        )
        atoms = {
            str(row.get("id") or "")
            for row in (checked.get("proved_constraints") or [])
            if isinstance(row, Mapping)
        }
        if checked.get("status") == "PROOF_CHECKED" and required_atoms.issubset(atoms):
            found.append({
                "concept_id": concept_id,
                "claim_kind": kind,
                "proved_atom_ids": sorted(atoms),
                "observation_id": observation_id,
                "outcome": outcome,
            })
    return found


def verify(
    case: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    repo_root: Any = None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(case, Mapping) or case.get("schema") != CASE_SCHEMA:
        return {
            "schema": SCHEMA, "verified": False,
            "errors": ["CASE_SCHEMA_INVALID"],
            "producer_independent": True, "terminal_authority": False,
        }
    if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
        return {
            "schema": SCHEMA, "verified": False,
            "errors": ["RESULT_SCHEMA_INVALID"],
            "producer_independent": True, "terminal_authority": False,
        }
    if set(case) != {"schema", "source_id", "source_text"}:
        errors.append("CASE_FIELD_SET_INVALID")
    source_id = str(case.get("source_id") or "").strip()
    source_text = case.get("source_text")
    if not source_id:
        errors.append("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text:
        errors.append("SOURCE_TEXT_REQUIRED")
        source_text = ""

    starts = []
    cursor = 0
    folded = source_text.casefold()
    needle = PHRASE.casefold()
    while True:
        at = folded.find(needle, cursor)
        if at < 0:
            break
        starts.append(at)
        cursor = at + 1
    if len(starts) != 1:
        errors.append("EXACTLY_ONE_DESCRIPTOR_OCCURRENCE_REQUIRED")

    supported = []
    sentence_span = None
    if not errors:
        start = starts[0]
        left, right, sentence = _sentence(source_text, start)
        sentence_span = [left, right]
        supported = _supported_concepts(sentence)
        if len(supported) != 1:
            errors.append("INDEPENDENT_CONTEXT_SIGNATURE_NOT_UNIQUE")

    matrix_result = None
    if not errors:
        matrix_result = matrix.verify_matrix(
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )
        if matrix_result.get("pass") is not True:
            errors.append("MATRIX_AUTHORITY_FAILED")
        else:
            row_by_id = {
                str(row.get("observation_id") or ""): row
                for row in (matrix_result.get("observations") or [])
                if isinstance(row, Mapping)
            }
            item = supported[0]
            row = row_by_id.get(item["observation_id"])
            if not isinstance(row, Mapping):
                errors.append("MATRIX_OBSERVATION_MISSING")
            elif (row.get("outcomes") or {}).get(item["concept_id"]) != item["outcome"]:
                errors.append("MATRIX_OUTCOME_BINDING_MISMATCH")

    expected_concept = supported[0]["concept_id"] if len(supported) == 1 else None
    if expected_concept is not None:
        if result.get("selected_concept_id") != expected_concept:
            errors.append("SELECTED_CONCEPT_MISMATCH")
        if result.get("candidate_ids") != list(CANDIDATES):
            errors.append("CANDIDATE_SET_MISMATCH")
        if result.get("candidate_scope_complete_for_task") is not True:
            errors.append("TASK_SCOPE_COMPLETENESS_MISSING")
        if result.get("global_phrase_identity_authority") is not False:
            errors.append("GLOBAL_IDENTITY_AUTHORITY_FORBIDDEN")
        if result.get("open_world_candidate_set_complete") is not False:
            errors.append("OPEN_WORLD_COMPLETENESS_FORBIDDEN")
        if result.get("source_id") != source_id:
            errors.append("SOURCE_ID_MISMATCH")
        if result.get("source_text_sha256") != _sha(source_text):
            errors.append("SOURCE_TEXT_SHA256_MISMATCH")

    return {
        "schema": SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_BOUNDED_REGCAP_CONTEXT_SELECTION_RECOMPUTED"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "producer_independent": True,
        "expected_concept_id": expected_concept,
        "independent_supported_signatures": supported,
        "sentence_span": sentence_span,
        "matrix_sha256": (
            matrix_result.get("matrix_sha256")
            if isinstance(matrix_result, Mapping) else None
        ),
        "semantic_identity_authority": False,
        "global_phrase_identity_authority": False,
        "open_world_candidate_set_complete": False,
        "terminal_authority": False,
        "boundary": (
            "INDEPENDENT_REPARSE_PLUS_LIVE_AUTHENTICATED_MATRIX__"
            "SELECTION_ONLY_WITHIN_EXPLICIT_THREE_RIVAL_TASK_UNIVERSE__"
            "NO_GLOBAL_PHRASE_IDENTITY_OR_OPEN_WORLD_COMPLETENESS"
        ),
    }
