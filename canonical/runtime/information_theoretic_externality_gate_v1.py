"""Strict proof-carrying information-theoretic externality gate.

A residual is never external because it is hard, blocked, unreplayable, or absent
from current durable state. External classification requires an exact two-world
witness O(W1)=O(W2), different required actions, exhaustive falsification of all
admitted internal bypass classes, and independently content-addressed proof
receipts bound to the exact claims they verify.

This module grants no terminal authority and no credit. It only validates the
externality proof object.
"""
from __future__ import annotations

from hashlib import sha256
import json
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


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, *, obligation_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "EXTERNALITY_NOT_PROVED",
        "pass": False,
        "information_theoretic_externality_proved": False,
        "irreducible_external_information_proved": False,
        "reason": reason,
        "obligation_ids": obligation_ids or [],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _pending_ids(pending: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        {
            str(row.get("work_id") or "")
            for row in pending
            if isinstance(row, Mapping) and str(row.get("work_id") or "")
        }
    )


def _valid_sha(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "")))


def _receipt_ok(
    value: Any,
    *,
    expected_statement_sha256: str,
    prover_id: str,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    if value.get("verified") is not True:
        return False
    if value.get("source_kind") not in {"INDEPENDENT_VERIFIER", "FORMAL_PROOF"}:
        return False
    verifier_id = str(value.get("verifier_id") or "").strip()
    if not verifier_id or verifier_id == prover_id:
        return False
    if value.get("verification_authority_mutated") is not False:
        return False
    statement_sha256 = str(value.get("statement_sha256") or "")
    evidence_sha256 = str(value.get("evidence_sha256") or "")
    receipt_sha256 = str(value.get("receipt_sha256") or "")
    if statement_sha256 != expected_statement_sha256:
        return False
    if not all(_valid_sha(x) for x in (
        statement_sha256,
        evidence_sha256,
        receipt_sha256,
    )):
        return False
    try:
        bound_payload = {
            str(k): v
            for k, v in value.items()
            if str(k) != "receipt_sha256"
        }
        return receipt_sha256 == _sha(bound_payload)
    except Exception:
        return False


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

    prover_id = str(certificate.get("prover_id") or "").strip()
    if not prover_id:
        return _fail("PROVER_ID_REQUIRED", obligation_ids=obligation_ids)

    claimed_ids = sorted(
        {str(x) for x in certificate.get("obligation_ids", []) if str(x)}
    )
    if claimed_ids != obligation_ids:
        return _fail("CERTIFICATE_OBLIGATION_SET_MISMATCH", obligation_ids=obligation_ids)

    missing_information = str(
        certificate.get("exact_missing_information_sha256") or ""
    )
    if not _valid_sha(missing_information):
        return _fail(
            "EXACT_MISSING_INFORMATION_BINDING_REQUIRED",
            obligation_ids=obligation_ids,
        )

    pair = certificate.get("world_pair")
    if not isinstance(pair, Mapping):
        return _fail(
            "INDISTINGUISHABLE_WORLD_PAIR_REQUIRED",
            obligation_ids=obligation_ids,
        )
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
    if not all(_valid_sha(x) for x in (obs1, obs2, act1, act2)):
        return _fail(
            "WORLD_BINDINGS_MUST_BE_CONTENT_ADDRESSED",
            obligation_ids=obligation_ids,
        )
    if obs1 != obs2:
        return _fail(
            "WORLDS_ARE_OBSERVATIONALLY_DISTINGUISHABLE",
            obligation_ids=obligation_ids,
        )
    if act1 == act2:
        return _fail(
            "WORLD_PAIR_DOES_NOT_REQUIRE_DIFFERENT_ACTIONS",
            obligation_ids=obligation_ids,
        )

    indistinguishability_statement = _sha({
        "claim": "OBSERVATIONAL_EQUIVALENCE",
        "obligation_ids": obligation_ids,
        "world_ids": [world_1_id, world_2_id],
        "accessible_observation_sha256": obs1,
    })
    if not _receipt_ok(
        certificate.get("indistinguishability_proof"),
        expected_statement_sha256=indistinguishability_statement,
        prover_id=prover_id,
    ):
        return _fail(
            "INDEPENDENT_INDISTINGUISHABILITY_PROOF_REQUIRED",
            obligation_ids=obligation_ids,
        )

    action_statement = _sha({
        "claim": "ACTION_SEPARATION",
        "obligation_ids": obligation_ids,
        "required_action_sha256_pair": [act1, act2],
    })
    if not _receipt_ok(
        certificate.get("action_separation_proof"),
        expected_statement_sha256=action_statement,
        prover_id=prover_id,
    ):
        return _fail(
            "INDEPENDENT_ACTION_SEPARATION_PROOF_REQUIRED",
            obligation_ids=obligation_ids,
        )

    exhaustion_statement = _sha({
        "claim": "INTERNAL_BYPASS_SET_EXHAUSTED",
        "obligation_ids": obligation_ids,
        "required_bypass_classes": list(REQUIRED_BYPASS_CLASSES),
    })
    if not _receipt_ok(
        certificate.get("internal_constructive_gap_exhaustion_proof"),
        expected_statement_sha256=exhaustion_statement,
        prover_id=prover_id,
    ):
        return _fail(
            "INTERNAL_CONSTRUCTIVE_GAP_EXHAUSTION_PROOF_REQUIRED",
            obligation_ids=obligation_ids,
        )

    rows = certificate.get("bypass_falsification")
    if not isinstance(rows, list):
        return _fail(
            "BYPASS_FALSIFICATION_SET_REQUIRED",
            obligation_ids=obligation_ids,
        )

    by_class: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail(
                "BYPASS_FALSIFICATION_ROW_INVALID",
                obligation_ids=obligation_ids,
            )
        cls = str(row.get("bypass_class") or "")
        if not cls or cls in by_class:
            return _fail(
                "BYPASS_FALSIFICATION_CLASS_DUPLICATE_OR_EMPTY",
                obligation_ids=obligation_ids,
            )
        by_class[cls] = row

    if set(by_class) != set(REQUIRED_BYPASS_CLASSES):
        return _fail(
            "BYPASS_FALSIFICATION_NOT_EXHAUSTIVE",
            obligation_ids=obligation_ids,
        )

    for cls in REQUIRED_BYPASS_CLASSES:
        row = by_class[cls]
        if row.get("verdict") != "FALSIFIED":
            return _fail(
                "BYPASS_NOT_FALSIFIED:" + cls,
                obligation_ids=obligation_ids,
            )
        bypass_statement = _sha({
            "claim": "BYPASS_FALSIFIED",
            "bypass_class": cls,
            "obligation_ids": obligation_ids,
        })
        if not _receipt_ok(
            row.get("proof"),
            expected_statement_sha256=bypass_statement,
            prover_id=prover_id,
        ):
            return _fail(
                "BYPASS_FALSIFICATION_PROOF_REQUIRED:" + cls,
                obligation_ids=obligation_ids,
            )

    certificate_core = {
        "schema": certificate.get("schema"),
        "status": certificate.get("status"),
        "prover_id": prover_id,
        "obligation_ids": obligation_ids,
        "exact_missing_information_sha256": missing_information,
        "world_pair": {
            "world_1": dict(w1),
            "world_2": dict(w2),
        },
        "indistinguishability_proof_receipt_sha256": certificate[
            "indistinguishability_proof"
        ]["receipt_sha256"],
        "action_separation_proof_receipt_sha256": certificate[
            "action_separation_proof"
        ]["receipt_sha256"],
        "internal_constructive_gap_exhaustion_proof_receipt_sha256": certificate[
            "internal_constructive_gap_exhaustion_proof"
        ]["receipt_sha256"],
        "bypass_falsification_receipt_sha256": {
            cls: by_class[cls]["proof"]["receipt_sha256"]
            for cls in REQUIRED_BYPASS_CLASSES
        },
    }
    core_digest = _sha(certificate_core)
    authority_statement = _sha({
        "claim": "EXTERNALITY_CERTIFICATE_VERIFIED",
        "certificate_core_sha256": core_digest,
    })
    authority = certificate.get("externality_verification_authority")
    if not _receipt_ok(
        authority,
        expected_statement_sha256=authority_statement,
        prover_id=prover_id,
    ):
        return _fail(
            "INDEPENDENT_EXTERNALITY_VERIFICATION_AUTHORITY_REQUIRED",
            obligation_ids=obligation_ids,
        )
    if str(authority.get("evidence_sha256") or "") != core_digest:
        return _fail(
            "EXTERNALITY_AUTHORITY_NOT_BOUND_TO_CERTIFICATE_CORE",
            obligation_ids=obligation_ids,
        )

    return {
        "schema": SCHEMA,
        "status": "PROVED_INFORMATION_THEORETICALLY_EXTERNAL",
        "pass": True,
        "information_theoretic_externality_proved": True,
        "irreducible_external_information_proved": True,
        "obligation_ids": obligation_ids,
        "exact_missing_information_sha256": missing_information,
        "indistinguishable_observation_sha256": obs1,
        "required_action_sha256_pair": [act1, act2],
        "required_bypass_classes": list(REQUIRED_BYPASS_CLASSES),
        "certificate_core_sha256": core_digest,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
