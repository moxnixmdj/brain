"""Information-theoretic externality gate.

This gate intentionally makes "external" expensive to claim.

A certificate must establish:
1. two distinct worlds are observationally indistinguishable to the Brain;
2. those worlds require different adequate actions;
3. every mandatory internal bypass class has a content-addressed proof that the
   route is unavailable or insufficient for the exact obligation;
4. the proof is scope-complete and independently/objectively grounded.

Anything weaker is INTERNAL_UNSOLVED.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INFORMATION_THEORETIC_EXTERNALITY_GATE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_INFORMATION_THEORETIC_EXTERNALITY_CERTIFICATE_V1"

MANDATORY_ROUTE_CLASSES = frozenset({
    "BRAIN_SEARCH",
    "EXTERNAL_SEARCH",
    "DERIVATION_OR_THEOREM",
    "COMPOSITION_OR_REUSE",
    "SYNTHESIS_OR_CODE",
    "SIMULATION",
    "EXPERIMENT_OR_REOBSERVATION",
    "WEAKER_SUFFICIENT_OBSERVATION",
    "ALTERNATE_ROUTE_OR_REFORMULATION",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "information_theoretic_externality_proved": False,
        "external_classification_authority": False,
        "terminal_authority": False,
        **extra,
    }


def verify_certificate(certificate: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        return _fail("CERTIFICATE_REQUIRED")
    c = dict(certificate)
    if c.get("schema") != CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID")
    obligation = str(c.get("target_obligation_id") or "").strip()
    if not obligation:
        return _fail("TARGET_OBLIGATION_ID_REQUIRED")
    if c.get("scope_complete") is not True:
        return _fail("SCOPE_COMPLETE_PROOF_REQUIRED")
    if c.get("independent_or_objective") is not True:
        return _fail("INDEPENDENT_OR_OBJECTIVE_PROOF_REQUIRED")

    witness = c.get("indistinguishability_witness")
    if not isinstance(witness, Mapping):
        return _fail("INDISTINGUISHABILITY_WITNESS_REQUIRED")
    w1 = str(witness.get("world_1_id") or "").strip()
    w2 = str(witness.get("world_2_id") or "").strip()
    obs1 = str(witness.get("world_1_observation_sha256") or "").lower()
    obs2 = str(witness.get("world_2_observation_sha256") or "").lower()
    a1 = str(witness.get("world_1_required_action_sha256") or "").lower()
    a2 = str(witness.get("world_2_required_action_sha256") or "").lower()
    if not w1 or not w2 or w1 == w2:
        return _fail("TWO_DISTINCT_WORLDS_REQUIRED")
    if not all(_HEX64.fullmatch(x) for x in (obs1, obs2, a1, a2)):
        return _fail("WITNESS_DIGEST_INVALID")
    if obs1 != obs2:
        return _fail("WORLDS_NOT_OBSERVATIONALLY_INDISTINGUISHABLE")
    if a1 == a2:
        return _fail("WORLDS_DO_NOT_REQUIRE_DIFFERENT_ACTIONS")

    rows = c.get("internal_route_falsification")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return _fail("INTERNAL_ROUTE_FALSIFICATION_REQUIRED")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail("INTERNAL_ROUTE_FALSIFICATION_ROW_INVALID")
        route = str(row.get("route_class") or "").strip()
        if route in seen:
            return _fail("DUPLICATE_ROUTE_CLASS:" + route)
        seen.add(route)
        if route not in MANDATORY_ROUTE_CLASSES:
            return _fail("UNKNOWN_ROUTE_CLASS:" + route)
        if row.get("status") != "PROVED_UNAVAILABLE_OR_INSUFFICIENT":
            return _fail("ROUTE_NOT_FALSIFIED:" + route)
        proof = str(row.get("proof_sha256") or "").lower()
        if not _HEX64.fullmatch(proof):
            return _fail("ROUTE_PROOF_SHA256_INVALID:" + route)
        if str(row.get("target_obligation_id") or "") != obligation:
            return _fail("ROUTE_OBLIGATION_BINDING_MISMATCH:" + route)

    missing = sorted(MANDATORY_ROUTE_CLASSES - seen)
    if missing:
        return _fail(
            "MANDATORY_ROUTE_CLASSES_NOT_EXHAUSTED",
            missing_route_classes=missing,
        )

    info = str(c.get("missing_information_class") or "").strip()
    if not info:
        return _fail("MISSING_INFORMATION_CLASS_REQUIRED")

    payload = {
        "target_obligation_id": obligation,
        "missing_information_class": info,
        "indistinguishability_witness": dict(witness),
        "internal_route_falsification": [dict(x) for x in rows],
        "scope_complete": True,
        "independent_or_objective": True,
    }
    return {
        "schema": SCHEMA,
        "status": "PASS__INFORMATION_THEORETIC_EXTERNALITY_PROVED",
        "pass": True,
        "information_theoretic_externality_proved": True,
        "external_classification_authority": True,
        "target_obligation_id": obligation,
        "missing_information_class": info,
        "certificate_digest": _digest(payload),
        "mandatory_route_class_count": len(MANDATORY_ROUTE_CLASSES),
        "terminal_authority": False,
    }
