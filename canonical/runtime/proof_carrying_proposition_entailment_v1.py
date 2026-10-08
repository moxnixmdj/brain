"""Proof-carrying whole-proposition entailment validator v1.

An untrusted proposer may suggest a chain from evidence proposition to claim.
Authority comes only from:
  1) mechanically checked built-in equivalences on a narrow exact grammar; or
  2) content-addressed semantic relation receipts plus independent verification
     receipts stored in canonical evidence/verification locations.

The checker composes only forward ENTAILS/EQUIVALENT steps. It never infers
lexical synonymy, polarity, paraphrase, world knowledge, or policy adequacy.
Unsupported steps fail closed.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROOF_CARRYING_PROPOSITION_ENTAILMENT_V1"
ROOT = Path(__file__).resolve().parents[2]

_CMP = re.compile(
    r"^(?P<subject>.+?)\s+is\s+(?P<op>at least|no less than|at most|no more than)\s+"
    r"(?P<num>[+-]?(?:\d+(?:\.\d*)?|\.\d+))$",
    re.I,
)
_ALLOWED_RELATIONS = {"ENTAILS", "EQUIVALENT"}
_REL_PREFIX = "canonical/evidence/semantic_relations/"
_VER_PREFIX = "canonical/verification/semantic_relations/"
_TEST_PREFIX = "canonical/tests/fixtures/semantic_relations/"


class EntailmentProofError(ValueError):
    pass


def _canon(value: Any) -> str:
    s = " ".join(str(value if value is not None else "").strip().split())
    while s.endswith((".", ";")):
        s = s[:-1].rstrip()
    return s.casefold()


def _git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _safe_path(path: str, *, expected_prefix: str, allow_test_fixtures: bool) -> Path:
    if not isinstance(path, str) or not path:
        raise EntailmentProofError("BOUND_PATH_REQUIRED")
    allowed = path.startswith(expected_prefix)
    if allow_test_fixtures and path.startswith(_TEST_PREFIX):
        allowed = True
    if not allowed:
        raise EntailmentProofError("BOUND_PATH_OUTSIDE_AUTHORIZED_PREFIX")
    candidate = (ROOT / path).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise EntailmentProofError("BOUND_PATH_ESCAPES_REPOSITORY") from exc
    if not candidate.is_file():
        raise EntailmentProofError("BOUND_FILE_NOT_FOUND")
    return candidate


def _read_bound_json(
    binding: Mapping[str, Any],
    *,
    expected_prefix: str,
    allow_test_fixtures: bool,
) -> tuple[dict[str, Any], str]:
    if not isinstance(binding, Mapping):
        raise EntailmentProofError("CONTENT_BINDING_REQUIRED")
    path = binding.get("path")
    sha = binding.get("git_blob_sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise EntailmentProofError("CONTENT_BINDING_SHA_INVALID")
    file_path = _safe_path(
        str(path or ""),
        expected_prefix=expected_prefix,
        allow_test_fixtures=allow_test_fixtures,
    )
    data = file_path.read_bytes()
    actual = _git_blob_sha_bytes(data)
    if actual != sha:
        raise EntailmentProofError("CONTENT_BINDING_BLOB_MISMATCH")
    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise EntailmentProofError("BOUND_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise EntailmentProofError("BOUND_JSON_OBJECT_REQUIRED")
    return payload, actual


def _numeric_signature(text: str) -> tuple[str, str, str] | None:
    m = _CMP.fullmatch(_canon(text))
    if not m:
        return None
    op = m.group("op").casefold()
    op_class = "GE" if op in {"at least", "no less than"} else "LE"
    try:
        number = format(Decimal(m.group("num")).normalize(), "f")
    except InvalidOperation:
        return None
    return (_canon(m.group("subject")), op_class, number)


def _check_numeric_equivalence(current: str, target: str) -> dict[str, Any]:
    left = _numeric_signature(current)
    right = _numeric_signature(target)
    if left is None or right is None:
        return {"pass": False, "reason": "OUTSIDE_MECHANICAL_NUMERIC_EQUIVALENCE_GRAMMAR"}
    if left != right:
        return {"pass": False, "reason": "NUMERIC_EQUIVALENCE_SIGNATURE_MISMATCH"}
    return {
        "pass": True,
        "relation": "EQUIVALENT",
        "signature": {"subject": left[0], "operator": left[1], "number": left[2]},
    }


def _check_certified_relation(
    current: str,
    target: str,
    step: Mapping[str, Any],
    *,
    allow_test_fixtures: bool,
) -> dict[str, Any]:
    relation_doc, relation_sha = _read_bound_json(
        step.get("relation_receipt"),
        expected_prefix=_REL_PREFIX,
        allow_test_fixtures=allow_test_fixtures,
    )
    verify_doc, verify_sha = _read_bound_json(
        step.get("verification_receipt"),
        expected_prefix=_VER_PREFIX,
        allow_test_fixtures=allow_test_fixtures,
    )
    if relation_doc.get("schema") != "PROJECT_BRAIN_SEMANTIC_PROPOSITION_RELATION_RECEIPT_V1":
        raise EntailmentProofError("RELATION_RECEIPT_SCHEMA_INVALID")
    relation = relation_doc.get("relation")
    if relation not in _ALLOWED_RELATIONS:
        raise EntailmentProofError("RELATION_KIND_UNSUPPORTED")
    if _canon(relation_doc.get("premise")) != _canon(current):
        raise EntailmentProofError("RELATION_PREMISE_MISMATCH")
    if _canon(relation_doc.get("hypothesis")) != _canon(target):
        raise EntailmentProofError("RELATION_HYPOTHESIS_MISMATCH")

    if verify_doc.get("schema") != "PROJECT_BRAIN_SEMANTIC_PROPOSITION_RELATION_VERIFICATION_V1":
        raise EntailmentProofError("VERIFICATION_RECEIPT_SCHEMA_INVALID")
    if verify_doc.get("pass") is not True:
        raise EntailmentProofError("VERIFICATION_RECEIPT_NOT_PASS")
    subject = verify_doc.get("subject")
    relation_binding = step.get("relation_receipt")
    if not isinstance(subject, Mapping) or not isinstance(relation_binding, Mapping):
        raise EntailmentProofError("VERIFICATION_SUBJECT_INVALID")
    if subject.get("path") != relation_binding.get("path") or subject.get("git_blob_sha") != relation_sha:
        raise EntailmentProofError("VERIFICATION_SUBJECT_BINDING_MISMATCH")
    if verify_doc.get("verified_relation") != relation:
        raise EntailmentProofError("VERIFIED_RELATION_MISMATCH")
    if _canon(verify_doc.get("verified_premise")) != _canon(current):
        raise EntailmentProofError("VERIFIED_PREMISE_MISMATCH")
    if _canon(verify_doc.get("verified_hypothesis")) != _canon(target):
        raise EntailmentProofError("VERIFIED_HYPOTHESIS_MISMATCH")

    return {
        "pass": True,
        "relation": relation,
        "relation_receipt_git_blob_sha": relation_sha,
        "verification_receipt_git_blob_sha": verify_sha,
        "relation_id": relation_doc.get("relation_id"),
    }


def verify_entailment(
    payload: Mapping[str, Any],
    *,
    allow_test_fixtures: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "reason": "PAYLOAD_MAPPING_REQUIRED", "terminal_authority": False}

    evidence = payload.get("evidence_text")
    claim = payload.get("claim_text")
    steps = payload.get("steps", [])
    if not isinstance(evidence, str) or not evidence.strip() or not isinstance(claim, str) or not claim.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "reason": "EVIDENCE_AND_CLAIM_TEXT_REQUIRED", "terminal_authority": False}
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False, "reason": "STEPS_SEQUENCE_REQUIRED", "terminal_authority": False}

    current = evidence
    audit: list[dict[str, Any]] = []
    try:
        for idx, step in enumerate(steps):
            if not isinstance(step, Mapping):
                raise EntailmentProofError(f"STEP_INVALID:{idx}")
            target = step.get("to_text")
            kind = step.get("kind")
            if not isinstance(target, str) or not target.strip():
                raise EntailmentProofError(f"STEP_TARGET_REQUIRED:{idx}")

            if kind == "MECHANICAL_NUMERIC_EQUIVALENCE":
                checked = _check_numeric_equivalence(current, target)
                if checked.get("pass") is not True:
                    raise EntailmentProofError(str(checked.get("reason")))
            elif kind == "CERTIFIED_PROPOSITION_RELATION":
                checked = _check_certified_relation(
                    current,
                    target,
                    step,
                    allow_test_fixtures=allow_test_fixtures,
                )
            else:
                raise EntailmentProofError(f"STEP_KIND_UNSUPPORTED:{kind}")

            audit.append({
                "index": idx,
                "kind": kind,
                "from_text_sha256": hashlib.sha256(current.encode()).hexdigest(),
                "to_text_sha256": hashlib.sha256(target.encode()).hexdigest(),
                **{k: v for k, v in checked.items() if k != "pass"},
            })
            current = target
    except EntailmentProofError as exc:
        return {
            "schema": SCHEMA,
            "status": "UNKNOWN__PROOF_CHAIN_NOT_VERIFIED",
            "pass": False,
            "reason": str(exc),
            "step_audit": audit,
            "predicate_truth": "UNKNOWN",
            "truthful_precommitment_observation": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if _canon(current) != _canon(claim):
        return {
            "schema": SCHEMA,
            "status": "UNKNOWN__PROOF_CHAIN_DOES_NOT_END_AT_CLAIM",
            "pass": False,
            "predicate_truth": "UNKNOWN",
            "truthful_precommitment_observation": False,
            "step_audit": audit,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__EVIDENCE_ENTAILS_CLAIM_BY_VERIFIED_PROOF_CHAIN",
        "pass": True,
        "predicate_truth": "TRUE",
        "truthful_precommitment_observation": True,
        "evidence_text_sha256": hashlib.sha256(evidence.encode()).hexdigest(),
        "claim_text_sha256": hashlib.sha256(claim.encode()).hexdigest(),
        "step_count": len(audit),
        "step_audit": audit,
        "proof_direction": "EVIDENCE_TO_CLAIM",
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": "WHOLE_PROPOSITION_FORWARD_ENTAILMENT_ONLY__NO_UNCHECKED_LEXICAL_SUBSTITUTION_OR_GENERAL_NLI",
    }
