"""Strict information-theoretic externality gate.

A hard or currently unsolved problem is never external by default.  This module
admits an external-information classification only when a proof-carrying
certificate shows that two currently observationally indistinguishable worlds
require different correct actions AND every declared internal bypass class has
been independently falsified.

This verifier grants no terminal authority.  It only verifies the structure and
content-addressed receipt bindings of an externality certificate supplied by a
separate proof producer.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INFORMATION_THEORETIC_EXTERNALITY_GATE_V1"
CERTIFICATE_SCHEMA = "PROJECT_BRAIN_INFORMATION_THEORETIC_EXTERNALITY_CERTIFICATE_V1"

REQUIRED_BYPASS_CLASSES = (
    "BRAIN_SEARCH",
    "EXTERNAL_SEARCH",
    "DEDUCTION_OR_THEOREM",
    "CAPABILITY_COMPOSITION",
    "NEW_SYNTHESIS_OR_CODE",
    "SIMULATION_OR_EXPERIMENT",
    "WEAKER_SUFFICIENT_OBSERVATION",
    "ALTERNATIVE_ROUTE",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _fail(reason: str, *, obligation_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "EXTERNALITY_NOT_PROVED",
        "pass": False,
        "irreducible_external_information_proved": False,
        "reason": reason,
        "obligation_ids": obligation_ids or [],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _pending_ids(pending: Sequence[Mapping[str, Any]]) -> list[str]:
    ids = sorted(
        {
            str(row.get("work_id") or "")
            for row in pending
            if isinstance(row, Mapping) and str(row.get("work_id") or "")
        }
    )
    return ids


def _receipt_ok(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    if value.get("verified") is not True:
        return False
    if value.get("source_kind") not in {"INDEPENDENT_VERIFIER", "FORMAL_PROOF"}:
        return False
    verifier_id = str(value.get("verifier_id") or "").strip()
    receipt_sha256 = str(value.get("receipt_sha256") or "")
    return bool(verifier_id) and bool(_SHA256.fullmatch(receipt_sha256))


def verify_certificate(
    certificate: Mapping[str, Any] | None,
    *,
    pending: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    obligation_ids = _pending_ids(pending)
    if not obligation_ids:
        return _fail("NO_PENDING_OBLIGATIONS_TO_CLASSIFY")

    if not isinstance(certificate, Mapping):
        return _fail(
            "PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED",
            obligation_ids=obligation_ids,
        )
    if certificate.get("schema") != CERTIFICATE_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID", obligation_ids=obligation_ids)
    if certificate.get("status") != "PROVED_INFORMATION_THEORETICALLY_EXTERNAL":
        return _fail("CERTIFICATE_STATUS_INVALID", obligation_ids=obligation_ids)

    claimed_ids = sorted({str(x) for x in certificate.get("obligation_ids", []) if str(x)})
    if claimed_ids != obligation_ids:
        return _fail("CERTIFICATE_OBLIGATION_SET_MISMATCH", obligation_ids=obligation_ids)

    missing_information = str(certificate.get("exact_missing_information_sha256") or "")
    if not _SHA256.fullmatch(missing_information):
        return _fail("EXACT_MISSING_INFORMATION_BINDING_REQUIRED", obligation_ids=obligation_ids)

    pair = certificate.get("world_pair")
    if not isinstance(pair, Mapping):
        return _fail("INDISTINGUISHABLE_WORLD_PAIR_REQUIRED", obligation_ids=obligation_ids)
    w1 = pair.get("world_1")
    w2 = pair.get("world_2")
    if not isinstance(w1, Mapping) or not isinstance(w2, Mapping):
        return _fail("WORLD_PAIR_INVALID", obligation_ids=obligation_ids)

    world_1_id = str(w1.get("world_id") or "")
    world_2_id = str(w2.get("world_id") or "")
    if not world_1_id or not world_2_id or world_1_id == world_2_id:
        return _fail("TWO_DISTINCT_WORLDS_REQUIRED", obligation_ids=obligation_ids)

    obs1 = str(w1.get("accessible_observation_sha256") or "")
    obs2 = str(w2.get("accessible_observation_sha256") or "")
    act1 = str(w1.get("required_action_sha256") or "")
    act2 = str(w2.get("required_action_sha256") or "")
    if not all(_SHA256.fullmatch(x) for x in (obs1, obs2, act1, act2)):
        return _fail("WORLD_BINDINGS_MUST_BE_CONTENT_ADDRESSED", obligation_ids=obligation_ids)
    if obs1 != obs2:
        return _fail("WORLDS_ARE_OBSERVATIONALLY_DISTINGUISHABLE", obligation_ids=obligation_ids)
    if act1 == act2:
        return _fail("WORLD_PAIR_DOES_NOT_REQUIRE_DIFFERENT_ACTIONS", obligation_ids=obligation_ids)

    if not _receipt_ok(certificate.get("indistinguishability_proof")):
        return _fail("INDEPENDENT_INDISTINGUISHABILITY_PROOF_REQUIRED", obligation_ids=obligation_ids)
    if not _receipt_ok(certificate.get("action_separation_proof")):
        return _fail("INDEPENDENT_ACTION_SEPARATION_PROOF_REQUIRED", obligation_ids=obligation_ids)
    if not _receipt_ok(certificate.get("internal_constructive_gap_exhaustion_proof")):
        return _fail("INTERNAL_CONSTRUCTIVE_GAP_EXHAUSTION_PROOF_REQUIRED", obligation_ids=obligation_ids)

    rows = certificate.get("bypass_falsification")
    if not isinstance(rows, list):
        return _fail("BYPASS_FALSIFICATION_SET_REQUIRED", obligation_ids=obligation_ids)

    by_class: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail("BYPASS_FALSIFICATION_ROW_INVALID", obligation_ids=obligation_ids)
        cls = str(row.get("bypass_class") or "")
        if not cls or cls in by_class:
            return _fail("BYPASS_FALSIFICATION_CLASS_DUPLICATE_OR_EMPTY", obligation_ids=obligation_ids)
        by_class[cls] = row

    if set(by_class) != set(REQUIRED_BYPASS_CLASSES):
        return _fail("BYPASS_FALSIFICATION_NOT_EXHAUSTIVE", obligation_ids=obligation_ids)

    for cls in REQUIRED_BYPASS_CLASSES:
        row = by_class[cls]
        if row.get("verdict") != "FALSIFIED":
            return _fail("BYPASS_NOT_FALSIFIED:" + cls, obligation_ids=obligation_ids)
        if not _receipt_ok(row.get("proof")):
            return _fail("BYPASS_FALSIFICATION_PROOF_REQUIRED:" + cls, obligation_ids=obligation_ids)

    authority = certificate.get("externality_verification_authority")
    if not _receipt_ok(authority):
        return _fail("INDEPENDENT_EXTERNALITY_VERIFICATION_AUTHORITY_REQUIRED", obligation_ids=obligation_ids)

    return {
        "schema": SCHEMA,
        "status": "PROVED_INFORMATION_THEORETICALLY_EXTERNAL",
        "pass": True,
        "irreducible_external_information_proved": True,
        "obligation_ids": obligation_ids,
        "exact_missing_information_sha256": missing_information,
        "indistinguishable_observation_sha256": obs1,
        "required_action_sha256_pair": [act1, act2],
        "required_bypass_classes": list(REQUIRED_BYPASS_CLASSES),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
