"""Source-aligned definitional entailment V1.

Proves a narrow but useful nonexplicit semantic relation:

    authenticated source facts + authenticated exact conjunctive concept definition
        -> directional entailment

The source does not have to name the target concept. Each source atom must be
independently authenticated against the exact raw source span. The target concept
definition must be independently authenticated for the exact scope. Missing source
atoms remain UNKNOWN unless an independent exact source-semantics completeness
certificate closes the source conjunction.

This is not a natural-language parser and does not trust lexical/model similarity,
caller labels, or unverified feature extraction. It grants no execution,
acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_DEFINITIONAL_ENTAILMENT_V1"
SOURCE_ATOM_AUTHORITY_SCHEMA = (
    "PROJECT_BRAIN_SOURCE_SEMANTIC_ATOM_AUTHORITY_RECEIPT_V1"
)
CONCEPT_DEFINITION_AUTHORITY_SCHEMA = (
    "PROJECT_BRAIN_CONCEPT_DEFINITION_AUTHORITY_RECEIPT_V1"
)
SOURCE_COMPLETENESS_AUTHORITY_SCHEMA = (
    "PROJECT_BRAIN_SOURCE_CONJUNCTIVE_COMPLETENESS_AUTHORITY_RECEIPT_V1"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DefinitionalEntailmentError(ValueError):
    pass


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


def _sha_ok(value: Any) -> bool:
    return _SHA256.fullmatch(str(value or "").lower()) is not None


def _normalized_definition(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DefinitionalEntailmentError("CONCEPT_DEFINITION_NOT_OBJECT")
    scope_id = str(value.get("scope_id") or "").strip()
    concept_id = str(value.get("concept_id") or "").strip()
    kind = str(value.get("definition_kind") or "").strip().upper()
    atoms_raw = value.get("definition_atoms")
    if not scope_id:
        raise DefinitionalEntailmentError("CONCEPT_DEFINITION_SCOPE_REQUIRED")
    if not concept_id:
        raise DefinitionalEntailmentError("CONCEPT_DEFINITION_ID_REQUIRED")
    if kind != "EXACT_CONJUNCTION":
        raise DefinitionalEntailmentError("CONCEPT_DEFINITION_KIND_UNSUPPORTED")
    if (
        not isinstance(atoms_raw, Sequence)
        or isinstance(atoms_raw, (str, bytes))
        or not atoms_raw
    ):
        raise DefinitionalEntailmentError("CONCEPT_DEFINITION_ATOMS_REQUIRED")
    atoms: list[str] = []
    for i, raw in enumerate(atoms_raw):
        if not isinstance(raw, str) or not raw.strip():
            raise DefinitionalEntailmentError(
                f"CONCEPT_DEFINITION_ATOM_INVALID:{i}"
            )
        atom = raw.strip()
        if atom in atoms:
            raise DefinitionalEntailmentError(
                "CONCEPT_DEFINITION_ATOM_DUPLICATE:" + atom
            )
        atoms.append(atom)
    return {
        "scope_id": scope_id,
        "concept_id": concept_id,
        "definition_kind": "EXACT_CONJUNCTION",
        "definition_atoms": sorted(atoms),
    }


def definition_sha256(value: Mapping[str, Any]) -> str:
    return _sha(_normalized_definition(value))


def _source_set_payload(
    *,
    source_id: str,
    scope_id: str,
    raw_span_sha256: str,
    atoms: Sequence[str],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "scope_id": scope_id,
        "raw_span_sha256": raw_span_sha256,
        "source_atom_ids": sorted(atoms),
    }


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "source_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _verify_source_atoms(
    receipts: Any,
    *,
    source_id: str,
    scope_id: str,
    raw_sha: str,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    if (
        not isinstance(receipts, Sequence)
        or isinstance(receipts, (str, bytes))
    ):
        raise DefinitionalEntailmentError("SOURCE_ATOM_RECEIPTS_NOT_SEQUENCE")
    if not callable(verifier):
        raise DefinitionalEntailmentError("SOURCE_ATOM_VERIFIER_REQUIRED")

    atoms: list[str] = []
    verified: list[dict[str, Any]] = []
    for i, raw in enumerate(receipts):
        if not isinstance(raw, Mapping):
            raise DefinitionalEntailmentError(
                f"SOURCE_ATOM_RECEIPT_NOT_OBJECT:{i}"
            )
        requested_atom = str(raw.get("atom_id") or "").strip()
        if not requested_atom:
            raise DefinitionalEntailmentError(
                f"SOURCE_ATOM_ID_REQUIRED:{i}"
            )
        if requested_atom in atoms:
            raise DefinitionalEntailmentError(
                "SOURCE_ATOM_ID_DUPLICATE:" + requested_atom
            )

        out = verifier(deepcopy(dict(raw)))
        if not isinstance(out, Mapping):
            raise DefinitionalEntailmentError(
                "SOURCE_ATOM_VERIFIER_RETURNED_NO_RECEIPT"
            )
        out = deepcopy(dict(out))
        expected = {
            "pass": True,
            "schema": SOURCE_ATOM_AUTHORITY_SCHEMA,
            "source_id": source_id,
            "scope_id": scope_id,
            "raw_span_sha256": raw_sha,
            "atom_id": requested_atom,
            "source_semantics_authenticated": True,
            "verification_authority_mutated": False,
        }
        bad = [key for key, value in expected.items() if out.get(key) != value]
        if not _sha_ok(out.get("receipt_sha256")):
            bad.append("receipt_sha256")
        if bad:
            raise DefinitionalEntailmentError(
                "SOURCE_ATOM_RECEIPT_BINDING_INVALID:"
                + ",".join(sorted(set(bad)))
            )
        atoms.append(requested_atom)
        verified.append(out)
    return sorted(atoms), verified


def _verify_definition(
    receipt: Any,
    *,
    scope_id: str,
    concept_id: str,
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(receipt, Mapping) or not callable(verifier):
        raise DefinitionalEntailmentError(
            "CONCEPT_DEFINITION_RECEIPT_AND_VERIFIER_REQUIRED"
        )
    out = verifier(deepcopy(dict(receipt)))
    if not isinstance(out, Mapping):
        raise DefinitionalEntailmentError(
            "CONCEPT_DEFINITION_VERIFIER_RETURNED_NO_RECEIPT"
        )
    out = deepcopy(dict(out))
    try:
        normalized = _normalized_definition(out)
    except DefinitionalEntailmentError as exc:
        raise DefinitionalEntailmentError(
            "CONCEPT_DEFINITION_BINDING_INVALID:" + str(exc)
        ) from exc

    bad: list[str] = []
    if out.get("pass") is not True:
        bad.append("pass")
    if out.get("schema") != CONCEPT_DEFINITION_AUTHORITY_SCHEMA:
        bad.append("schema")
    if normalized["scope_id"] != scope_id:
        bad.append("scope_id")
    if normalized["concept_id"] != concept_id:
        bad.append("concept_id")
    if out.get("definition_semantics_authenticated") is not True:
        bad.append("definition_semantics_authenticated")
    if out.get("verification_authority_mutated") is not False:
        bad.append("verification_authority_mutated")
    if out.get("definition_sha256") != definition_sha256(normalized):
        bad.append("definition_sha256")
    if not _sha_ok(out.get("receipt_sha256")):
        bad.append("receipt_sha256")
    if bad:
        raise DefinitionalEntailmentError(
            "CONCEPT_DEFINITION_BINDING_INVALID:"
            + ",".join(sorted(set(bad)))
        )
    return normalized, out


def _verify_source_completeness(
    receipt: Any,
    *,
    source_id: str,
    scope_id: str,
    raw_sha: str,
    proved_atoms: Sequence[str],
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> tuple[bool, dict[str, Any] | None]:
    if receipt is None:
        return False, None
    if not isinstance(receipt, Mapping) or not callable(verifier):
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_RECEIPT_AND_VERIFIER_REQUIRED"
        )
    out = verifier(deepcopy(dict(receipt)))
    if not isinstance(out, Mapping):
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_VERIFIER_RETURNED_NO_RECEIPT"
        )
    out = deepcopy(dict(out))

    atoms_raw = out.get("source_atom_ids")
    if (
        not isinstance(atoms_raw, Sequence)
        or isinstance(atoms_raw, (str, bytes))
    ):
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_ATOMS_INVALID"
        )
    atoms: list[str] = []
    for i, raw in enumerate(atoms_raw):
        if not isinstance(raw, str) or not raw.strip():
            raise DefinitionalEntailmentError(
                f"SOURCE_COMPLETENESS_ATOM_INVALID:{i}"
            )
        atom = raw.strip()
        if atom in atoms:
            raise DefinitionalEntailmentError(
                "SOURCE_COMPLETENESS_ATOM_DUPLICATE:" + atom
            )
        atoms.append(atom)
    atoms = sorted(atoms)

    unproved = sorted(set(atoms) - set(proved_atoms))
    if unproved:
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_CONTAINS_UNPROVED_ATOMS:"
            + ",".join(unproved)
        )
    if set(proved_atoms) - set(atoms):
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_OMITS_PROVED_ATOMS"
        )

    payload = _source_set_payload(
        source_id=source_id,
        scope_id=scope_id,
        raw_span_sha256=raw_sha,
        atoms=atoms,
    )
    bad: list[str] = []
    if out.get("pass") is not True:
        bad.append("pass")
    if out.get("schema") != SOURCE_COMPLETENESS_AUTHORITY_SCHEMA:
        bad.append("schema")
    for key, value in payload.items():
        if out.get(key) != value:
            bad.append(key)
    if out.get("source_atom_set_sha256") != _sha(payload):
        bad.append("source_atom_set_sha256")
    if out.get("exact_conjunctive_source_semantics_complete") is not True:
        bad.append("exact_conjunctive_source_semantics_complete")
    if out.get("verification_authority_mutated") is not False:
        bad.append("verification_authority_mutated")
    if not _sha_ok(out.get("receipt_sha256")):
        bad.append("receipt_sha256")
    if bad:
        raise DefinitionalEntailmentError(
            "SOURCE_COMPLETENESS_BINDING_INVALID:"
            + ",".join(sorted(set(bad)))
        )
    return True, out


def prove(
    *,
    raw_span: str,
    source_id: str,
    scope_id: str,
    left_id: str,
    right_id: str,
    source_atom_receipts: Sequence[Mapping[str, Any]],
    source_atom_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    concept_definition_receipt: Mapping[str, Any],
    concept_definition_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    source_completeness_receipt: Mapping[str, Any] | None = None,
    source_completeness_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(raw_span, str) or not raw_span.strip():
            raise DefinitionalEntailmentError("RAW_SPAN_REQUIRED")
        source_id = str(source_id or "").strip()
        scope_id = str(scope_id or "").strip()
        left_id = str(left_id or "").strip()
        right_id = str(right_id or "").strip()
        if not source_id:
            raise DefinitionalEntailmentError("SOURCE_ID_REQUIRED")
        if not scope_id:
            raise DefinitionalEntailmentError("SCOPE_ID_REQUIRED")
        if not left_id or not right_id or left_id == right_id:
            raise DefinitionalEntailmentError(
                "DISTINCT_LEFT_RIGHT_IDS_REQUIRED"
            )

        raw_sha = sha256(raw_span.encode("utf-8")).hexdigest()
        source_atoms, verified_source = _verify_source_atoms(
            source_atom_receipts,
            source_id=source_id,
            scope_id=scope_id,
            raw_sha=raw_sha,
            verifier=source_atom_verifier,
        )
        definition, verified_definition = _verify_definition(
            concept_definition_receipt,
            scope_id=scope_id,
            concept_id=right_id,
            verifier=concept_definition_verifier,
        )
        source_complete, verified_completeness = _verify_source_completeness(
            source_completeness_receipt,
            source_id=source_id,
            scope_id=scope_id,
            raw_sha=raw_sha,
            proved_atoms=source_atoms,
            verifier=source_completeness_verifier,
        )

        source_set = set(source_atoms)
        target_set = set(definition["definition_atoms"])
        missing_target = sorted(target_set - source_set)
        source_only = sorted(source_set - target_set)

        # Exact-conjunction target semantics make all target conjuncts jointly
        # sufficient for target membership. Source completeness is unnecessary
        # for this forward direction: extra/unknown source meaning can only make
        # the source more specific.
        left_entails = not missing_target

        # Reverse entailment requires knowing the source's entire conjunctive
        # meaning. Without source completeness, do not turn missing source facts
        # into a claim about what the source does not mean.
        right_entails = bool(source_complete and source_set <= target_set)

        left_disproved = bool(source_complete and not left_entails)
        right_disproved = bool(source_complete and not right_entails)
        equivalent = left_entails and right_entails

        if equivalent:
            strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
        elif left_entails:
            strongest = "LEFT_ENTAILS_RIGHT"
        elif right_entails:
            strongest = "RIGHT_ENTAILS_LEFT"
        else:
            strongest = "UNKNOWN"

        return _base(
            "PASS__SOURCE_ALIGNED_DEFINITIONAL_ENTAILMENT_CHECKED",
            passed=True,
            source_id=source_id,
            scope_id=scope_id,
            left_id=left_id,
            right_id=right_id,
            raw_span_sha256=raw_sha,
            source_atom_ids=source_atoms,
            target_definition_atoms=definition["definition_atoms"],
            source_semantics_complete=source_complete,
            missing_target_atoms=missing_target,
            source_only_atoms=source_only,
            logical_equivalence_in_scope=equivalent,
            left_entails_right=left_entails,
            right_entails_left=right_entails,
            left_entails_right_disproved=left_disproved,
            right_entails_left_disproved=right_disproved,
            logical_equivalence_disproved=left_disproved or right_disproved,
            strongest_proved_relation=strongest,
            verified_source_atom_receipts=verified_source,
            verified_concept_definition_receipt=verified_definition,
            verified_source_completeness_receipt=verified_completeness,
            theorem_boundary=(
                "EXACT_ONLY_FOR_INDEPENDENTLY_AUTHENTICATED_SOURCE_ATOMS_AND_"
                "AN_INDEPENDENTLY_AUTHENTICATED_EXACT_CONJUNCTIVE_CONCEPT_"
                "DEFINITION__REVERSE_ENTAILMENT_REQUIRES_INDEPENDENT_EXACT_"
                "SOURCE_CONJUNCTIVE_COMPLETENESS"
            ),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            passed=False,
            reason=type(exc).__name__ + ":" + str(exc),
        )
